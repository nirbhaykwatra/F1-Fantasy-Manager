from datetime import datetime, timezone
from typing import List, Optional
from io import BytesIO
import discord
import zoneinfo
import pytz
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from f1bot.config import load_config
from f1bot.utils.logger import BotLogger
from f1bot.services.models import (
    PlayerRepository,
    Player,
    LeagueRepository,
    League,
    DraftRepository,
    PlayerLeague,
    Draft,
    GrandPrixRepository,
    DriverRepository,
    ConstructorRepository,
    PlayerRoundScoreRepository,
    CounterpickRepository,
    SeasonRepository,
    DriverExhaustionRepository
)

config = load_config()

class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.player_repository = PlayerRepository(self.bot.db)
        self.league_repository = LeagueRepository(self.bot.db)
        self.draft_repository = DraftRepository(self.bot.db)
        self.grand_prix_repository = GrandPrixRepository(self.bot.db)
        self.driver_repository = DriverRepository(self.bot.db)
        self.constructor_repository = ConstructorRepository(self.bot.db)
        self.player_round_score_repository = PlayerRoundScoreRepository(self.bot.db)
        self.counterpick_repository = CounterpickRepository(self.bot.db)
        self.season_repository = SeasonRepository(self.bot.db)
        self.exhaustion_repository = DriverExhaustionRepository(self.bot.db)
        self.draft_service = self.bot.draftService
        self.embedService = self.bot.embedService

    async def league_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        """Autocomplete callback for league choices"""
        return await self.bot.choiceService.get_league_choices(interaction.guild_id)

    async def constructor_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for constructor choices"""
        return await self.bot.choiceService.get_constructor_choices(interaction.guild_id)

    async def driver_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for driver choices"""
        return await self.bot.choiceService.get_driver_choices(interaction.guild_id)

    async def grand_prix_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for grand prix choices"""
        return await self.bot.choiceService.get_grand_prix_choices(interaction.guild_id)

    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to join',
                           timezone='Your local timezone. Use /timezones to show a list of available timezones. Copy the timezone name exactly as it appears in the list.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def register(self, interaction: discord.Interaction, league: str, team_name: str, team_motto: str,
                       timezone: str):
        BotLogger.log_command_invocation(
            command_name="register",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league,
            team_name=team_name,
            timezone=timezone
        )

        try:
            # If entered timezone is invalid, send error message and return
            if timezone not in zoneinfo.available_timezones():
                BotLogger.log_command_error("register", interaction.user.name,
                                            ValueError(f"Invalid timezone: {timezone}"))
                await interaction.response.send_message(
                    f'Invalid timezone! Please use /timezones to see a list of available timezones.', ephemeral=True)
                return

            # Search for league by id
            league_id = int(league)
            league_object: League | None = await self.league_repository.get_league_by_id(league_id)

            # If no league is found, send error message and return
            if league_object is None:
                BotLogger.log_command_error("register", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.response.send_message(f'League with id {league_id} not found!', ephemeral=True)
                return

            # Get list of leagues the user is registered in
            player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(
                interaction.user.id)

            # If user is already registered for league, send error message and return
            if league_object in player_leagues:
                BotLogger.log_command_error("register", interaction.user.name,
                                            ValueError(f"Already registered in league: {league_object.name}"))
                await interaction.response.send_message(f'You are already registered for {league_object.name}!',
                                                        ephemeral=True)
                return

            # Search for player by discord id
            player_if_exists = await self.player_repository.get_player_by_discord_id(interaction.user.id)

            # If player is already in the database, just add them to the selected league and send success message
            if player_if_exists:
                await self.player_repository.add_player_to_league(league_id=league_id, player_id=player_if_exists.id,
                                                                  team_name=team_name, team_motto=team_motto)
                BotLogger.log_command_success("register", interaction.user.name,
                                              f"Added existing player to league: {league_object.name}")
                await interaction.response.send_message(f'Successfully registered for {league_object.name}!',
                                                        ephemeral=True)
                return

            # If player is not in the database, create a new player and add them to the selected league
            created_player = await self.player_repository.create_player(
                discord_user_id=interaction.user.id,
                username=interaction.user.name,
                timezone=timezone,
            )
            player_league = await self.player_repository.add_player_to_league(league_id=league_id,
                                                                              player_id=created_player.id,
                                                                              team_name=team_name,
                                                                              team_motto=team_motto)

            # If player was successfully registered, send success message
            if created_player and player_league is not None:
                BotLogger.log_command_success("register", interaction.user.name,
                                              f"Created new player and registered to league: {league_object.name}")
                await interaction.response.send_message(f'Successfully registered for {league_object.name}!',
                                                        ephemeral=True)
            else:
                BotLogger.log_command_error("register", interaction.user.name,
                                            Exception("Failed to create player or add to league"))
                await interaction.response.send_message(
                    f'Failed to register for {league_object.name}. Please check your input options and try again.',
                    ephemeral=True)

        except Exception as e:
            BotLogger.log_command_error("register", interaction.user.name, e)
            raise

    @app_commands.command(name='unregister', description='Unregister from a league!')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to unregister from')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def unregister(self, interaction: discord.Interaction, league: str):
        BotLogger.log_command_invocation(
            command_name="unregister",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league
        )

        try:
            player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not player:
                BotLogger.log_command_error("unregister", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not registered!"),
                    ephemeral=True
                )
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("unregister", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("unregister", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return
            # Search for league by id
            league_id = int(league)
            league_object: League | None = await self.league_repository.get_league_by_id(league_id)
            # If no league is found, send error message and return
            if league_object is None:
                BotLogger.log_command_error("unregister", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.response.send_message(f'League with id {league_id} not found!', ephemeral=True)
                return
            # Get player leagues by Discord ID
            player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(
                interaction.user.id)
            # If user is not registered for league, send error message and return
            if league_object not in player_leagues:
                BotLogger.log_command_error("unregister", interaction.user.name,
                                            ValueError(f"Not registered in league: {league_object.name}"))
                await interaction.response.send_message(f'You are not registered in {league_object.name}!',
                                                        ephemeral=True)
                return

            # Get player by Discord ID
            player: Player | None = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            # Try to remove player from league
            await self.player_repository.remove_player_from_league(league_id=league_id, player_id=player.id)

            # Get player leagues by Discord ID again
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)
            # If the player is not registered in any leagues and unregisters, also remove F1 Fantasy Player role
            if len(player_leagues) == 0:
                await self.player_repository.delete_player(interaction.user.id)
                role = discord.utils.get(interaction.guild.roles, name="F1 Fantasy Player")
                if role:
                    await interaction.user.remove_roles(role)
                BotLogger.log_command_success("unregister", interaction.user.name,
                                              f"Removed from league and deleted player: {league_object.name}")
                await interaction.response.send_message(f'You are no longer registered in any leagues!', ephemeral=True)
                return
            else:
                BotLogger.log_command_success("unregister", interaction.user.name,
                                              f"Unregistered from league: {league_object.name}")
                await interaction.response.send_message(f'Successfully unregistered from {league_object.name}!',
                                                        ephemeral=True)

        except Exception as e:
            BotLogger.log_command_error("unregister", interaction.user.name, e)
            raise

    @app_commands.command(name='draft', description='Draft your team for the selected round!')
    @app_commands.autocomplete(
        league=league_autocomplete,
        driver1=driver_autocomplete,
        driver2=driver_autocomplete,
        driver3=driver_autocomplete,
        bogey=driver_autocomplete,
        team=constructor_autocomplete,
        race=grand_prix_autocomplete
    )
    @app_commands.describe(
        league='The league you want to draft for',
        driver1='The first driver you want to draft',
        driver2='The second driver you want to draft',
        driver3='The third driver you want to draft',
        bogey='The bogey driver you want to draft',
        team='The constructor you want to draft',
        race='The Grand Prix you want to draft for (optional)'
    )
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def draft(self, interaction: discord.Interaction, league: str, driver1: str, driver2: str, driver3: str,
                    bogey: str, team: str, race: str = None):
        BotLogger.log_command_invocation(
            command_name="draft",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league,
            driver1=driver1,
            driver2=driver2,
            driver3=driver3,
            bogey=bogey,
            team=team,
            race=race
        )

        await interaction.response.defer(ephemeral=True)

        try:
            # Get player
            player: Player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not player:
                BotLogger.log_command_error("draft", interaction.user.name, ValueError("Player not registered"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "You are not registered. Please use /register to sign up first."), ephemeral=True)
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            # Parse league ID
            try:
                league_id = int(league)
            except ValueError:
                BotLogger.log_command_error("draft", interaction.user.name, ValueError(f"Invalid league ID: {league}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("That league does not exist!"),
                    ephemeral=True)
                return

            # Check if player is in this league
            is_in_league = await self.player_repository.is_player_in_league(player.id, league_id)
            if not is_in_league:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError(f"Player not in league: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("You are not a member of this league!"),
                    ephemeral=True)
                return

            # Get the league and season
            league_obj = await self.league_repository.get_league_by_id(league_id)
            if not league_obj:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("League not found."), ephemeral=True)
                return

            # Get next/upcoming Grand Prix
            if race:
                grand_prix = await self.grand_prix_repository.get_grand_prix_by_id(int(race))
            else:
                grand_prix = await self.grand_prix_repository.get_next_grand_prix(league_obj.season_id)

            if not grand_prix:
                BotLogger.log_command_error("draft", interaction.user.name, ValueError("No upcoming Grand Prix found"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "No upcoming Grand Prix found for drafting."), ephemeral=True)
                return

            # Parse driver and constructor IDs
            try:
                driver1_id = int(driver1)
                driver2_id = int(driver2)
                driver3_id = int(driver3)
                wildcard_id = int(bogey)
                constructor_id = int(team)
            except ValueError as e:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError(f"Invalid driver or constructor selection: {str(e)}"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "Invalid driver or constructor selection."), ephemeral=True)
                return

            # Submit draft using the service
            draft, error = await self.draft_service.submit_draft(
                player_id=player.id,
                league_id=league_id,
                grand_prix_id=grand_prix.id,
                driver1_id=driver1_id,
                driver2_id=driver2_id,
                driver3_id=driver3_id,
                wildcard_id=wildcard_id,
                constructor_id=constructor_id,
                is_auto_assigned=False
            )

            if error:
                # Draft validation failed
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError(f"Draft validation failed: {error}"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(error),
                                                ephemeral=True)
                return

            # Get draft details for confirmation
            draft_info = await self.draft_service.get_draft_info(
                player.id, league_id, grand_prix.id
            )

            if not draft_info:
                BotLogger.log_command_error("draft", interaction.user.name,
                                            ValueError("Failed to retrieve draft information"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("Failed to retrieve draft information."),
                    ephemeral=True)
                return

            embed = await self.embedService.create_draft_success_embed(league_obj=league_obj, grand_prix=grand_prix,
                                                                       draft_info=draft_info, player_obj=player)

            BotLogger.log_command_success("draft", interaction.user.name,
                                          f"Draft submitted for {grand_prix.event_name} in {league_obj.name}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            BotLogger.log_command_error("draft", interaction.user.name, e)
            await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                f"An unexpected error has occurred: {str(e)}."), ephemeral=True)

    @app_commands.checks.has_any_role("Administrator")
    @app_commands.command(name='admin-draft', description='Draft your team for the selected round!')
    @app_commands.autocomplete(
        league=league_autocomplete,
        driver1=driver_autocomplete,
        driver2=driver_autocomplete,
        driver3=driver_autocomplete,
        bogey=driver_autocomplete,
        team=constructor_autocomplete,
        race=grand_prix_autocomplete
    )
    @app_commands.describe(
        league='The league you want to draft for',
        driver1='The first driver you want to draft',
        driver2='The second driver you want to draft',
        driver3='The third driver you want to draft',
        bogey='The bogey driver you want to draft',
        team='The constructor you want to draft',
        race='The Grand Prix you want to draft for (optional)'
    )
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def admin_draft(self, interaction: discord.Interaction, league: str, user: discord.User, driver1: str,
                          driver2: str, driver3: str,
                          bogey: str, team: str, race: str = None):
        BotLogger.log_command_invocation(
            command_name="admin-draft",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league,
            target_user=user.name,
            driver1=driver1,
            driver2=driver2,
            driver3=driver3,
            bogey=bogey,
            team=team,
            race=race
        )

        await interaction.response.defer(ephemeral=True)

        try:
            # Get player
            player: Player = await self.player_repository.get_player_by_discord_id(user.id)
            if not player:
                BotLogger.log_command_error("admin-draft", interaction.user.name, ValueError("Player not registered"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "You are not registered. Please use /register to sign up first."), ephemeral=True)
                return

            # Parse league ID
            try:
                league_id = int(league)
            except ValueError:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError(f"Invalid league ID: {league}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("That league does not exist!"),
                    ephemeral=True)
                return

            # Check if player is in this league
            is_in_league = await self.player_repository.is_player_in_league(player.id, league_id)
            if not is_in_league:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError(f"Player not in league: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("You are not a member of this league!"),
                    ephemeral=True)
                return

            # Get the league and season
            league_obj = await self.league_repository.get_league_by_id(league_id)
            if not league_obj:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("League not found."), ephemeral=True)
                return

            # Get next/upcoming Grand Prix
            if race:
                grand_prix = await self.grand_prix_repository.get_grand_prix_by_id(int(race))
            else:
                grand_prix = await self.grand_prix_repository.get_next_grand_prix(league_obj.season_id)

            if not grand_prix:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError("No upcoming Grand Prix found"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "No upcoming Grand Prix found for drafting."), ephemeral=True)
                return

            # Parse driver and constructor IDs
            try:
                driver1_id = int(driver1)
                driver2_id = int(driver2)
                driver3_id = int(driver3)
                wildcard_id = int(bogey)
                constructor_id = int(team)
            except ValueError as e:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError(f"Invalid driver or constructor selection: {str(e)}"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                    "Invalid driver or constructor selection."), ephemeral=True)
                return

            # Submit draft using the service
            draft, error = await self.draft_service.submit_draft(
                player_id=player.id,
                league_id=league_id,
                grand_prix_id=grand_prix.id,
                driver1_id=driver1_id,
                driver2_id=driver2_id,
                driver3_id=driver3_id,
                wildcard_id=wildcard_id,
                constructor_id=constructor_id,
                is_auto_assigned=False
            )

            if error:
                # Draft validation failed
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError(f"Draft validation failed: {error}"))
                await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(error),
                                                ephemeral=True)
                return

            # Get draft details for confirmation
            draft_info = await self.draft_service.get_draft_info(
                player.id, league_id, grand_prix.id
            )

            if not draft_info:
                BotLogger.log_command_error("admin-draft", interaction.user.name,
                                            ValueError("Failed to retrieve draft information"))
                await interaction.followup.send(
                    embed=await self.embedService.create_draft_failure_embed("Failed to retrieve draft information."),
                    ephemeral=True)
                return

            embed = await self.embedService.create_draft_success_embed(league_obj=league_obj, grand_prix=grand_prix,
                                                                       draft_info=draft_info, player_obj=player)

            BotLogger.log_command_success("admin-draft", interaction.user.name,
                                          f"Admin draft submitted for {user.name} in {grand_prix.event_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            BotLogger.log_command_error("admin-draft", interaction.user.name, e)
            await interaction.followup.send(embed=await self.embedService.create_draft_failure_embed(
                f"An unexpected error has occurred: {str(e)}."), ephemeral=True)

    @app_commands.command(name='profile', description="View yours or another user's profile!")
    @app_commands.describe(user='The user you want to view. Leave blank to view your own profile.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        target_user = user if user else interaction.user
        BotLogger.log_command_invocation(
            command_name="profile",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            target_user=target_user.name
        )

        await interaction.response.defer(ephemeral=True)

        try:
            player: Optional[Player] = await self.player_repository.get_player_by_discord_id(
                discord_user_id=target_user.id)

            if player is None:
                BotLogger.log_command_error("profile", interaction.user.name,
                                            ValueError(f"Player not found: {target_user.name}"))
                if user is None:
                    await interaction.followup.send(f'You are not registered in any leagues!', ephemeral=True)
                else:
                    await interaction.followup.send(f'The selected user is not registered in any leagues!',
                                                    ephemeral=True)
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("profile", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("profile", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            # Create list of embeds
            embeds = []

            # First embed: Player's general information
            first_embed = discord.Embed(
                title=f"{target_user.display_name}'s Profile",
                description="Player Information",
                color=discord.Color.from_str("#e8272a")
            )
            first_embed.set_thumbnail(url=target_user.display_avatar.url)
            first_embed.add_field(name="Username", value=player.username, inline=True)
            first_embed.add_field(name="Timezone", value=player.timezone, inline=True)
            first_embed.add_field(name="Registered Leagues", value=str(len(player_leagues)), inline=False)

            # List all leagues
            if player_leagues:
                league_list = "\n".join([f"• {league.name}" for league in player_leagues])
                first_embed.add_field(name="Leagues", value=league_list, inline=False)

            embeds.append(first_embed)

            # Additional embeds: One per league with team info and current draft
            if len(player_leagues) > 0:
                for league in player_leagues:
                    # Get player's league-specific info
                    player_league_info: Optional[PlayerLeague] = await self.player_repository.get_player_league_info(
                        player_id=player.id,
                        league_id=league.id
                    )

                    # Get the next/current grand prix for this league's season
                    next_gp = await self.grand_prix_repository.get_next_grand_prix(season_id=league.season_id)

                    # Create league-specific embed
                    league_embed = discord.Embed(
                        title=player_league_info.team_name if player_league_info and player_league_info.team_name else "Team Name Not Set",
                        description=f"**League:** {league.name}",
                        color=discord.Color.from_rgb(
                            (league.embed_color >> 16) & 0xFF,
                            (league.embed_color >> 8) & 0xFF,
                            league.embed_color & 0xFF
                        )
                    )
                    league_embed.set_thumbnail(url=target_user.display_avatar.url)

                    # Add team motto if available
                    if player_league_info and player_league_info.team_motto:
                        league_embed.add_field(name="Team Motto", value=player_league_info.team_motto, inline=False)

                        # Add season statistics for this league
                        season_stats = await self.player_round_score_repository.get_player_season_stats(
                            player_id=player.id,
                            league_id=league.id
                        )
                        if season_stats:
                            stats_text = (
                                f"**Total Points:** {season_stats['total_points']}\n"
                                f"**Highest Round:** {season_stats['best_round_score']}\n"
                                f"**Lowest Round:** {season_stats['worst_round_score']}\n"
                                f"**Average Points:** {season_stats['avg_points_per_round']}"
                            )
                            league_embed.add_field(name="Season Statistics", value=stats_text, inline=False)

                    # Get current draft if there's an active/upcoming GP
                    if next_gp:
                        # Check if we should redact draft information
                        should_redact = False
                        if user is not None and next_gp.draft_deadline_utc:
                            now = datetime.now(timezone.utc)
                            if now <= next_gp.draft_deadline_utc:
                                should_redact = True

                        current_draft: Optional[Draft] = await self.draft_repository.get_draft(
                            player_id=player.id,
                            league_id=league.id,
                            grand_prix_id=next_gp.id
                        )

                        if current_draft:
                            if should_redact:
                                # Redact team information - deadline hasn't passed and viewing another user
                                league_embed.add_field(
                                    name=f"**Round {next_gp.round_number}: {next_gp.event_name}**",
                                    value="🔒 Team information hidden until draft deadline",
                                    inline=False
                                )
                            else:
                                # Get driver names for the draft
                                driver1 = await self.driver_repository.get_driver_by_id(current_draft.driver1_id)
                                driver2 = await self.driver_repository.get_driver_by_id(current_draft.driver2_id)
                                driver3 = await self.driver_repository.get_driver_by_id(current_draft.driver3_id)
                                wildcard = await self.driver_repository.get_driver_by_id(current_draft.wildcard_id)
                                constructor = await self.constructor_repository.get_constructor_by_id(
                                    current_draft.constructor_id)

                                league_embed.add_field(name=f"**Round {next_gp.round_number}: {next_gp.event_name}**",
                                                       value="",
                                                       inline=False)
                                if driver1:
                                    league_embed.add_field(name=f"{driver1.first_name} {driver1.last_name}",
                                                           value=f"Driver 1",
                                                           inline=True)
                                if driver2:
                                    league_embed.add_field(name=f"{driver2.first_name} {driver2.last_name}",
                                                           value=f"Driver 2",
                                                           inline=True)
                                if driver3:
                                    league_embed.add_field(name=f"{driver3.first_name} {driver3.last_name}",
                                                           value=f"Driver 3",
                                                           inline=True)
                                if wildcard:
                                    league_embed.add_field(name=f"{wildcard.first_name} {wildcard.last_name}",
                                                           value=f"🎲Bogey Driver🎲", inline=True)
                                if constructor:
                                    league_embed.add_field(name=f"{constructor.full_name}", value=f"🏎️Constructor🏎️",
                                                           inline=True)
                        else:
                            league_embed.add_field(
                                name="Current Draft",
                                value=f"No draft submitted for {next_gp.event_name}",
                                inline=False
                            )
                    else:
                        league_embed.add_field(name="Current Draft", value="No active Grand Prix", inline=False)

                    embeds.append(league_embed)

            # Create pagination view and send
            if len(embeds) == 1:
                # Only one page, no need for pagination
                embeds[0].set_footer(text=f"Requested by {interaction.user.display_name}",
                                     icon_url=interaction.user.display_avatar.url)
                await interaction.followup.send(embed=embeds[0], ephemeral=True)
            else:
                # Multiple pages, use pagination
                view = ProfilePaginationView(embeds, interaction.user)
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

            BotLogger.log_command_success("profile", interaction.user.name, f"Profile displayed for {target_user.name}")

        except Exception as e:
            BotLogger.log_command_error("profile", interaction.user.name, e)
            raise

    @app_commands.command(name='timezones', description='List all available timezones.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def timezones(self, interaction: discord.Interaction):
        BotLogger.log_command_invocation(
            command_name="timezones",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id
        )

        try:
            timezones = sorted(zoneinfo.available_timezones())
            embeds = []
            current_embed = discord.Embed(title="Available Timezones",
                                          description="Copy your timezone exactly as shown and paste it into the 'timezone' field in /register.",
                                          color=discord.Color.blurple())
            fields = 0
            for tz in timezones:
                current_embed.add_field(name=tz, value="")
                fields += 1
                if fields == 25:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(title="Available Timezones",
                                                  description="Copy your timezone exactly as shown and paste it into the 'timezone' field in /register.",
                                                  color=discord.Color.blurple())
                    fields = 0

            # Add the last embed if it has any fields
            if fields > 0:
                embeds.append(current_embed)

            # Create pagination view
            view = TimezonePaginationView(embeds)
            await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

            BotLogger.log_command_success("timezones", interaction.user.name,
                                          f"Displayed {len(embeds)} pages of timezones")

        except Exception as e:
            BotLogger.log_command_error("timezones", interaction.user.name, e)
            raise

    # For the following commands, try out using discord ui instead of simple embeds.
    @app_commands.command(name='team', description='View your team.')
    @app_commands.autocomplete(grand_prix=grand_prix_autocomplete)
    @app_commands.describe(user='The user you want to view. Leave blank to view your own team.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def team(self, interaction: discord.Interaction, user: discord.User = None, grand_prix: str = None):
        target_user = user if user else interaction.user
        BotLogger.log_command_invocation(
            command_name="team",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            target_user=target_user.name,
            grand_prix=grand_prix
        )

        await interaction.response.defer(ephemeral=True)

        try:
            player: Optional[Player] = await self.player_repository.get_player_by_discord_id(
                discord_user_id=target_user.id)

            if player is None:
                BotLogger.log_command_error("team", interaction.user.name,
                                            ValueError(f"Player not found: {target_user.name}"))
                if user is None:
                    await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues!"), ephemeral=True)
                else:
                    await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                        "The selected user is not registered in any leagues!"), ephemeral=True)
                return

            # Get all leagues the player is in
            player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(
                target_user.id)

            if len(player_leagues) == 0:
                BotLogger.log_command_error("team", interaction.user.name,
                                            ValueError(f"Player not in any leagues: {target_user.name}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        f'{"You are" if user is None else f"{target_user.display_name} is"} not registered in any leagues!'),
                    ephemeral=True)
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("team", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            # Create list of embeds - one per league
            embeds = []

            for league in player_leagues:
                # Get player's league-specific info
                player_league_info: Optional[PlayerLeague] = await self.player_repository.get_player_league_info(
                    player_id=player.id,
                    league_id=league.id
                )

                # Get all GPs for this season to find previous and next
                all_gps = await self.grand_prix_repository.list_grands_prix_by_season(season_id=league.season_id)

                # Find the next GP and the previous completed GP
                next_gp = None
                prev_gp = None

                for gp in all_gps:
                    if not gp.is_completed and next_gp is None:
                        next_gp = gp
                    elif gp.is_completed:
                        prev_gp = gp

                # Create league-specific embed
                league_embed = discord.Embed(
                    title=player_league_info.team_name if player_league_info and player_league_info.team_name else "Team Name Not Set",
                    description=f"**League:** {league.name}",
                    color=discord.Color.from_rgb(
                        (league.embed_color >> 16) & 0xFF,
                        (league.embed_color >> 8) & 0xFF,
                        league.embed_color & 0xFF
                    )
                )
                league_embed.set_thumbnail(url=target_user.display_avatar.url)

                # Add team motto if available
                if player_league_info and player_league_info.team_motto:
                    league_embed.add_field(name="Team Motto", value=player_league_info.team_motto, inline=False)

                if grand_prix is not None:
                    next_gp = await self.grand_prix_repository.get_grand_prix_by_id(int(grand_prix))
                    prev_gp = None

                # Get and display CURRENT draft (next GP)
                if next_gp:
                    # Check if we should redact draft information
                    should_redact = False
                    if user is not None and next_gp.draft_deadline_utc:
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        if now <= next_gp.draft_deadline_utc:
                            should_redact = True

                    current_draft: Optional[Draft] = await self.draft_repository.get_draft(
                        player_id=player.id,
                        league_id=league.id,
                        grand_prix_id=next_gp.id
                    )

                    if current_draft:
                        if should_redact:
                            # Redact team information - deadline hasn't passed and viewing another user
                            league_embed.add_field(
                                name=f"**Round {next_gp.round_number}: {next_gp.event_name}**",
                                value="🔒 Team information hidden until draft deadline",
                                inline=False
                            )
                        else:
                            driver1 = await self.driver_repository.get_driver_by_id(current_draft.driver1_id)
                            driver2 = await self.driver_repository.get_driver_by_id(current_draft.driver2_id)
                            driver3 = await self.driver_repository.get_driver_by_id(current_draft.driver3_id)
                            wildcard = await self.driver_repository.get_driver_by_id(current_draft.wildcard_id)
                            constructor = await self.constructor_repository.get_constructor_by_id(
                                current_draft.constructor_id)

                            league_embed.add_field(name=f"**Round {next_gp.round_number}: {next_gp.event_name}**",
                                                   value="", inline=False)
                            if driver1:
                                league_embed.add_field(name=f"{driver1.first_name} {driver1.last_name}",
                                                       value=f"Driver 1", inline=True)
                            if driver2:
                                league_embed.add_field(name=f"{driver2.first_name} {driver2.last_name}",
                                                       value=f"Driver 2", inline=True)
                            if driver3:
                                league_embed.add_field(name=f"{driver3.first_name} {driver3.last_name}",
                                                       value=f"Driver 3", inline=True)
                            if wildcard:
                                league_embed.add_field(name=f"{wildcard.first_name} {wildcard.last_name}",
                                                       value=f"🎲Bogey Driver🎲", inline=True)
                            if constructor:
                                league_embed.add_field(name=f"{constructor.full_name}", value=f"🏎️Constructor🏎️",
                                                       inline=True)
                    else:
                        league_embed.add_field(
                            name="Current Draft",
                            value=f"No draft submitted for {next_gp.event_name}",
                            inline=False
                        )
                else:
                    league_embed.add_field(name="Current Draft", value="No upcoming Grand Prix", inline=False)

                # Get and display PREVIOUS draft (last completed GP)
                if prev_gp:
                    previous_draft: Optional[Draft] = await self.draft_repository.get_draft(
                        player_id=player.id,
                        league_id=league.id,
                        grand_prix_id=prev_gp.id
                    )

                    if previous_draft:
                        prev_driver1 = await self.driver_repository.get_driver_by_id(previous_draft.driver1_id)
                        prev_driver2 = await self.driver_repository.get_driver_by_id(previous_draft.driver2_id)
                        prev_driver3 = await self.driver_repository.get_driver_by_id(previous_draft.driver3_id)
                        prev_wildcard = await self.driver_repository.get_driver_by_id(previous_draft.wildcard_id)
                        prev_constructor = await self.constructor_repository.get_constructor_by_id(
                            previous_draft.constructor_id)

                        league_embed.add_field(name=f"**Round {prev_gp.round_number}: {prev_gp.event_name}**", value="",
                                               inline=False)
                        if prev_driver1:
                            league_embed.add_field(name=f"{prev_driver1.first_name} {prev_driver1.last_name}",
                                                   value=f"Driver 1",
                                                   inline=True)
                        if prev_driver2:
                            league_embed.add_field(name=f"{prev_driver2.first_name} {prev_driver2.last_name}",
                                                   value=f"Driver 2",
                                                   inline=True)
                        if prev_driver3:
                            league_embed.add_field(name=f"{prev_driver3.first_name} {prev_driver3.last_name}",
                                                   value=f"Driver 3",
                                                   inline=True)
                        if prev_wildcard:
                            league_embed.add_field(name=f"{prev_wildcard.first_name} {prev_wildcard.last_name}",
                                                   value=f"🎲Bogey Driver🎲", inline=True)
                        if prev_constructor:
                            league_embed.add_field(name=f"{prev_constructor.full_name}", value=f"🏎️Constructor🏎️",
                                                   inline=True)

                    else:
                        league_embed.add_field(
                            name="Previous Draft",
                            value=f"No draft submitted for {prev_gp.event_name}",
                            inline=False
                        )
                else:
                    if grand_prix is None:
                        league_embed.add_field(name="Previous Draft", value="No completed Grand Prix", inline=False)

                embeds.append(league_embed)

            # Create pagination view and send
            if len(embeds) == 1:
                # Only one page, no need for pagination
                embeds[0].set_footer(text=f"Requested by {interaction.user.display_name}",
                                     icon_url=interaction.user.display_avatar.url)
                await interaction.followup.send(embed=embeds[0], ephemeral=True)
            else:
                # Multiple pages, use pagination
                view = TeamPaginationView(embeds, interaction.user)
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

            BotLogger.log_command_success("team", interaction.user.name,
                                          f"Team displayed for {target_user.name} across {len(embeds)} league(s)")

        except Exception as e:
            BotLogger.log_command_error("team", interaction.user.name, e)
            raise

    @app_commands.command(name='counterpick',
                          description='Counterpick another player for the selected round in your league.')
    @app_commands.autocomplete(league=league_autocomplete, driver=driver_autocomplete,
                               grand_prix=grand_prix_autocomplete)
    @app_commands.describe(
        league='The league you want to counterpick in',
        user='The user you want to counterpick against',
        driver='The driver you want to counterpick',
        grand_prix='The Grand Prix you want to counterpick for (optional - defaults to upcoming GP)'
    )
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def counterpick(self, interaction: discord.Interaction, league: str, user: discord.User, driver: str,
                          grand_prix: str = None):
        BotLogger.log_command_invocation(
            command_name="counterpick",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league,
            target_user=user.name,
            driver=driver,
            grand_prix=grand_prix
        )

        await interaction.response.defer(ephemeral=True)

        try:
            player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not player:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not registered!"),
                    ephemeral=True
                )
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("exhausted", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return
            # Get the picking player
            picking_player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not picking_player:
                BotLogger.log_command_error("counterpick", interaction.user.name, ValueError("Player not registered"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    "You are not registered! Please use /register to sign up first."), ephemeral=True)
                return

            # Get the target player
            target_player = await self.player_repository.get_player_by_discord_id(user.id)
            if not target_player:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Target player not registered: {user.name}"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    f"{user.display_name} is not registered!"), ephemeral=True)
                return

            # Can't counterpick yourself
            if picking_player.id == target_player.id:
                BotLogger.log_command_error("counterpick", interaction.user.name, ValueError("Cannot counterpick self"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You cannot counterpick yourself!"),
                    ephemeral=True)
                return

            # Parse league ID
            try:
                league_id = int(league)
            except ValueError:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Invalid league ID: {league}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Invalid league selection!"),
                    ephemeral=True)
                return

            # Check if picking player is in this league
            is_picking_in_league = await self.player_repository.is_player_in_league(picking_player.id, league_id)
            if not is_picking_in_league:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Picker not in league: {league_id}"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    "You are not a member of this league!"), ephemeral=True)
                return

            # Check if target player is in this league
            is_target_in_league = await self.player_repository.is_player_in_league(target_player.id, league_id)
            if not is_target_in_league:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Target not in league: {user.name}"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    f"{user.display_name} is not a member of this league!"), ephemeral=True)
                return

            # Get the league object
            league_obj = await self.league_repository.get_league_by_id(league_id)
            if not league_obj:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("League not found!"), ephemeral=True)
                return

            # Get Grand Prix - either specified or next/upcoming
            if grand_prix:
                try:
                    grand_prix_id = int(grand_prix)
                    gp_obj = await self.grand_prix_repository.get_grand_prix_by_id(grand_prix_id)
                    if not gp_obj:
                        BotLogger.log_command_error("counterpick", interaction.user.name,
                                                    ValueError(f"Grand Prix not found: {grand_prix_id}"))
                        await interaction.followup.send(
                            embed=await self.embedService.create_generic_failure_embed("Grand Prix not found!"),
                            ephemeral=True)
                        return
                    # Verify GP belongs to this league's season
                    if gp_obj.season_id != league_obj.season_id:
                        BotLogger.log_command_error("counterpick", interaction.user.name,
                                                    ValueError(f"Grand Prix not in league season"))
                        await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                            "This Grand Prix is not part of the selected league's season!"), ephemeral=True)
                        return
                    gp_obj = gp_obj
                except ValueError:
                    BotLogger.log_command_error("counterpick", interaction.user.name,
                                                ValueError(f"Invalid Grand Prix ID: {grand_prix}"))
                    await interaction.followup.send(
                        embed=await self.embedService.create_generic_failure_embed("Invalid Grand Prix selection!"),
                        ephemeral=True)
                    return
            else:
                gp_obj = await self.grand_prix_repository.get_next_grand_prix(league_obj.season_id)
                if not gp_obj:
                    BotLogger.log_command_error("counterpick", interaction.user.name,
                                                ValueError("No upcoming Grand Prix found"))
                    await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                        "No upcoming Grand Prix found for counterpicking!"), ephemeral=True)
                    return

            # Check if counterpick deadline has passed
            if gp_obj.counterpick_deadline_utc:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if now > gp_obj.counterpick_deadline_utc:
                    deadline_utc = gp_obj.counterpick_deadline_utc
                    deadline_tz = deadline_utc.astimezone()
                    deadline_str = deadline_tz.strftime('%Y-%m-%d %I:%M %p')
                    BotLogger.log_command_error("counterpick", interaction.user.name,
                                                ValueError(f"Deadline passed: {deadline_str}"))
                    await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                        f"Counterpick deadline has passed (was {deadline_str})."), ephemeral=True)
                    return

            # Parse driver ID
            try:
                driver_id = int(driver)
            except ValueError:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Invalid driver ID: {driver}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Invalid driver selection!"),
                    ephemeral=True)
                return

            # Get the driver object
            driver_obj = await self.driver_repository.get_driver_by_id(driver_id)
            if not driver_obj:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Driver not found: {driver_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Driver not found!"), ephemeral=True)
                return

            # Check if counterpick is allowed using repository validation
            can_counterpick, reason = await self.counterpick_repository.can_counterpick(
                picking_player_id=picking_player.id,
                target_player_id=target_player.id,
                grand_prix_id=gp_obj.id,
                league_id=league_id,
                season_id=league_obj.season_id
            )

            if not can_counterpick:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError(f"Counterpick not allowed: {reason}"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    f"**Counterpick not allowed**\n\n{reason}"), ephemeral=True)
                return

            # Create the counterpick
            counterpick = await self.counterpick_repository.create_counterpick(
                grand_prix_id=gp_obj.id,
                league_id=league_id,
                picking_player_id=picking_player.id,
                target_player_id=target_player.id,
                target_driver_id=driver_id
            )

            if not counterpick:
                BotLogger.log_command_error("counterpick", interaction.user.name,
                                            ValueError("Failed to create counterpick"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Counterpick failed! Please try again."),
                    ephemeral=True)
                return

            # Get remaining counterpicks
            remaining = await self.counterpick_repository.get_remaining_counterpicks(
                picking_player.id, league_id, league_obj.season_id
            )

            # Create success embed
            embed = discord.Embed(
                title="COUNTERPICK ANNOUNCEMENT",
                description=f"**{gp_obj.event_name}** (Round {gp_obj.round_number})",
                color=league_obj.embed_color
            )

            embed.add_field(
                name="🏹 Picking Player",
                value=f"{picking_player.username}",
                inline=True
            )

            embed.add_field(
                name="🎯 Target",
                value=f"{user.display_name}",
                inline=True
            )

            embed.add_field(
                name="🚫 Banned Driver",
                value=f"{driver_obj.first_name} {driver_obj.last_name} ({driver_obj.code})",
                inline=True
            )

            embed.add_field(
                name="📊 Remaining Counterpicks",
                value=f"{picking_player.username} has {remaining} counterpicks left this season",
                inline=False
            )

            if gp_obj.counterpick_deadline_utc:
                deadline_ts = int(gp_obj.counterpick_deadline_utc.timestamp())
                embed.add_field(
                    name="⏰ Counterpick Deadline",
                    value=f"<t:{deadline_ts}:F>",
                    inline=False
                )

            embed.set_footer(text=f"League: {league_obj.name} | You can update your counterpick until the deadline")

            await interaction.channel.send(embed=embed)
            await interaction.followup.send(embed=embed, ephemeral=False)

            BotLogger.log_command_success("counterpick", interaction.user.name,
                                          f"Counterpicked {driver_obj.first_name} {driver_obj.last_name} against {user.name} for {gp_obj.event_name}")

        except ValueError as e:
            # Handle database-level validation errors
            error_msg = str(e)
            BotLogger.log_command_error("counterpick", interaction.user.name, e)
            if "Counterpick limit exceeded" in error_msg:
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    f"Counterpick limit exceeded!\n\n{error_msg}"), ephemeral=True)
            elif "already has maximum 2 counterpicks" in error_msg:
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    f"{target_player.username} already has 2 counterpicks against them!\n\n{error_msg}"),
                                                ephemeral=True)
            else:
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(f"Error: {error_msg}"), ephemeral=True)
        except Exception as e:
            BotLogger.log_command_error("counterpick", interaction.user.name, e)
            await interaction.followup.send(
                embed=await self.embedService.create_generic_failure_embed(f"An unexpected error occurred: {str(e)}"),
                ephemeral=True)

    @app_commands.command(name='cancel-counterpick', description='Cancel your counterpick for a specific Grand Prix.')
    @app_commands.autocomplete(league=league_autocomplete, grand_prix=grand_prix_autocomplete)
    @app_commands.describe(
        league='The league where you want to cancel your counterpick',
        grand_prix='The Grand Prix for which you want to cancel your counterpick'
    )
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def cancel_counterpick(self, interaction: discord.Interaction, league: str, grand_prix: str):
        BotLogger.log_command_invocation(
            command_name="cancel-counterpick",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league,
            grand_prix=grand_prix
        )

        await interaction.response.defer(ephemeral=True)

        try:
            player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not player:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not registered!"),
                    ephemeral=True
                )
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            # Parse league ID
            league_id = int(league)
            league_obj = await self.league_repository.get_league_by_id(league_id)
            if not league_obj:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("League not found!"),
                    ephemeral=True
                )
                return

            # Parse Grand Prix ID
            try:
                grand_prix_id = int(grand_prix)
            except ValueError:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError(f"Invalid Grand Prix ID: {grand_prix}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Invalid Grand Prix selection!"),
                    ephemeral=True
                )
                return

            # Get the Grand Prix
            gp_obj = await self.grand_prix_repository.get_grand_prix_by_id(grand_prix_id)
            if not gp_obj:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError(f"Grand Prix not found: {grand_prix_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Grand Prix not found!"),
                    ephemeral=True
                )
                return

            # Verify GP belongs to this league's season
            if gp_obj.season_id != league_obj.season_id:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("Grand Prix not in league season"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "This Grand Prix is not part of the selected league's season!"
                    ),
                    ephemeral=True
                )
                return

            # Check if GP is already completed
            if gp_obj.is_completed:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError(f"GP already completed: {gp_obj.event_name}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        f"Cannot cancel counterpick - {gp_obj.event_name} has already been completed!"
                    ),
                    ephemeral=True
                )
                return

            # Check if counterpick deadline has passed
            if gp_obj.counterpick_deadline_utc:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if now > gp_obj.counterpick_deadline_utc:
                    BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                                ValueError("Deadline passed"))
                    await interaction.followup.send(
                        embed=await self.embedService.create_generic_failure_embed(
                            f"Cannot cancel - counterpick deadline for {gp_obj.event_name} has passed!"
                        ),
                        ephemeral=True
                    )
                    return

            # Check if counterpick exists
            existing = await self.counterpick_repository.get_counterpick(
                grand_prix_id=grand_prix_id,
                league_id=league_id,
                picking_player_id=player.id
            )

            if not existing:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("No counterpick found"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        f"You don't have an active counterpick for {gp_obj.event_name} in {league_obj.name}!"
                    ),
                    ephemeral=True
                )
                return

            # Get target player and driver info for confirmation
            target_player = await self.player_repository.get_player_by_id(existing.target_player_id)
            target_driver = await self.driver_repository.get_driver_by_id(existing.target_driver_id)

            # Delete the counterpick
            success = await self.counterpick_repository.delete_counterpick(
                grand_prix_id=grand_prix_id,
                league_id=league_id,
                picking_player_id=player.id
            )

            if success:
                # Get updated remaining counterpicks
                remaining = await self.counterpick_repository.get_remaining_counterpicks(
                    player.id, league_id, league_obj.season_id
                )

                # Create public announcement embed
                embed = discord.Embed(
                    title="COUNTERPICK CANCELLATION",
                    description=f"**{gp_obj.event_name}** (Round {gp_obj.round_number})",
                    color=league_obj.embed_color
                )

                embed.add_field(
                    name="🏹 Player",
                    value=interaction.user.display_name,
                    inline=True
                )

                if target_player:
                    embed.add_field(
                        name="🎯 Previously Targeted",
                        value=target_player.username,
                        inline=True
                    )

                if target_driver:
                    embed.add_field(
                        name="🔓 Unbanned Driver",
                        value=f"{target_driver.first_name} {target_driver.last_name} ({target_driver.code})",
                        inline=True
                    )

                embed.add_field(
                    name="📊 Remaining Counterpicks",
                    value=f"{interaction.user.display_name} now has {remaining} counterpicks left this season",
                    inline=False
                )

                embed.set_footer(text=f"League: {league_obj.name}")

                # Send public announcement
                await interaction.channel.send(embed=embed)

                # Send ephemeral confirmation to user
                await interaction.followup.send(
                    content="✅ Counterpick cancelled successfully!",
                    ephemeral=True
                )

                BotLogger.log_command_success("cancel-counterpick", interaction.user.name,
                                              f"Cancelled counterpick for {gp_obj.event_name} in {league_obj.name}")
            else:
                BotLogger.log_command_error("cancel-counterpick", interaction.user.name,
                                            ValueError("Failed to delete counterpick"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "Failed to cancel counterpick. Please try again."
                    ),
                    ephemeral=True
                )

        except Exception as e:
            BotLogger.log_command_error("cancel-counterpick", interaction.user.name, e)
            await interaction.followup.send(
                embed=await self.embedService.create_generic_failure_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )

    @app_commands.guilds(discord.Object(id=config.guild_id))
    @app_commands.command(name='my-counterpicks', description='View your active counterpicks across all leagues.')
    async def my_counterpicks(self, interaction: discord.Interaction):
        BotLogger.log_command_invocation(
            command_name="my-counterpicks",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id
        )

        await interaction.response.defer(ephemeral=True)

        try:
            player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if not player:
                BotLogger.log_command_error("my-counterpicks", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not registered!"),
                    ephemeral=True
                )
                return

            # Get all leagues the player is in
            player_leagues = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("my-counterpicks", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True
                )
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("my-counterpicks", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            # Collect all counterpicks across all leagues
            all_counterpicks_with_data = []

            for league in player_leagues:
                # Get ALL counterpicks for this player in this league (not just next GP)
                all_counterpicks = await self.counterpick_repository.get_counterpicks_for_player_in_league(
                    player_id=player.id,
                    league_id=league.id
                )

                if not all_counterpicks:
                    continue

                # Filter to only future/active GPs and collect data
                for cp in all_counterpicks:
                    gp = await self.grand_prix_repository.get_grand_prix_by_id(cp.grand_prix_id)
                    if gp and not gp.is_completed:
                        target_player = await self.player_repository.get_player_by_id(cp.target_player_id)
                        target_driver = await self.driver_repository.get_driver_by_id(cp.target_driver_id)
                        all_counterpicks_with_data.append({
                            'counterpick': cp,
                            'grand_prix': gp,
                            'league': league,
                            'target_player': target_player,
                            'target_driver': target_driver
                        })

            if not all_counterpicks_with_data:
                embed = discord.Embed(
                    title="🎯 Your Active Counterpicks",
                    description="You don't have any active counterpicks for upcoming Grand Prix events.",
                    color=discord.Color.blue()
                )
                BotLogger.log_command_success("my-counterpicks", interaction.user.name, "No active counterpicks found")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Sort by round number
            all_counterpicks_with_data.sort(key=lambda x: x['grand_prix'].round_number)

            # Create embeds for pagination - one per counterpick
            embeds = []
            for data in all_counterpicks_with_data:
                cp = data['counterpick']
                gp = data['grand_prix']
                league = data['league']
                target_player = data['target_player']
                target_driver = data['target_driver']

                # Create embed with league color
                embed = discord.Embed(
                    title="Counterpicks",
                    description=f"**{gp.event_name}** (Round {gp.round_number})",
                    color=league.embed_color
                )

                embed.add_field(
                    name="📍 League",
                    value=league.name,
                    inline=False
                )

                embed.add_field(
                    name="🏹 Picking Player",
                    value=player.username,
                    inline=True
                )

                if target_player:
                    embed.add_field(
                        name="🎯 Target",
                        value=target_player.username,
                        inline=True
                    )

                if target_driver:
                    embed.add_field(
                        name="🚫 Banned Driver",
                        value=f"{target_driver.first_name} {target_driver.last_name} ({target_driver.code})",
                        inline=True
                    )

                # Get remaining counterpicks for this league
                remaining = await self.counterpick_repository.get_remaining_counterpicks(
                    player.id, league.id, league.season_id
                )

                embed.add_field(
                    name="📊 Remaining Counterpicks",
                    value=f"You have {remaining} counterpicks left this season in {league.name}",
                    inline=False
                )

                if gp.counterpick_deadline_utc:
                    deadline_ts = int(gp.counterpick_deadline_utc.timestamp())
                    embed.add_field(
                        name="⏰ Counterpick Deadline",
                        value=f"<t:{deadline_ts}:F>",
                        inline=False
                    )

                embeds.append(embed)

            # Create pagination view with cancel button
            if len(embeds) == 1:
                # Only one counterpick, no need for pagination but show cancel button
                embeds[0].set_footer(text=f"Use /cancel-counterpick to remove this counterpick")
                view = CounterpickPaginationView(embeds, all_counterpicks_with_data, interaction.user, self)
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)
            else:
                # Multiple counterpicks, use pagination
                view = CounterpickPaginationView(embeds, all_counterpicks_with_data, interaction.user, self)
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

            BotLogger.log_command_success("my-counterpicks", interaction.user.name,
                                          f"Displayed {len(embeds)} active counterpick(s)")

        except Exception as e:
            BotLogger.log_command_error("my-counterpicks", interaction.user.name, e)
            await interaction.followup.send(
                embed=await self.embedService.create_generic_failure_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name='grand-prix', description='View the details of a specific grand prix.')
    @app_commands.autocomplete(grand_prix=grand_prix_autocomplete)
    @app_commands.describe(grand_prix='The grand prix you want to view')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def grand_prix(self, interaction: discord.Interaction, grand_prix: str):
        BotLogger.log_command_invocation(
            command_name="grand-prix",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            grand_prix=grand_prix
        )

        BotLogger.log_command_error("grand-prix", interaction.user.name,
                                    NotImplementedError("Command not yet implemented"))
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

    @app_commands.command(name='points', description='View the current points table for the selected league.')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to view')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def points(self, interaction: discord.Interaction, league: str):
        BotLogger.log_command_invocation(
            command_name="points",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            league=league
        )

        await interaction.response.defer()

        try:
            league_id = int(league)
            league_obj = await self.league_repository.get_league_by_id(league_id)

            if not league_obj:
                BotLogger.log_command_error("points", interaction.user.name,
                                            ValueError(f"League not found: {league_id}"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("League not found!"),
                    ephemeral=True)
                return

            # Get all players in the league
            players_in_league = await self.player_repository.list_players_in_league(league_id)

            if not players_in_league:
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("No players found in this league!"),
                    ephemeral=True)
                return

            # Get all GPs for the season
            all_gps = await self.grand_prix_repository.list_grands_prix_by_season(league_obj.season_id)

            if not all_gps:
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "No Grand Prix events found for this season!"),
                    ephemeral=True)
                return

            # Find the most recent completed GP (for the title)
            most_recent_completed_gp = None
            for gp in all_gps:
                if gp.is_completed:
                    most_recent_completed_gp = gp

            # Build player data with scores
            player_data = []
            for player in players_in_league:
                player_league_info = await self.player_repository.get_player_league_info(player.id, league_id)

                # Get scores for all GPs
                gp_scores = {}
                total = 0
                for gp in all_gps:
                    score = await self.player_round_score_repository.get_score(player.id, league_id, gp.id)
                    if score:
                        gp_scores[gp.id] = score.total_points
                        total += score.total_points
                    else:
                        gp_scores[gp.id] = '-'

                player_data.append({
                    'player_name': player.username,
                    'team_name': player_league_info.team_name if player_league_info and player_league_info.team_name else 'No Team Name',
                    'gp_scores': gp_scores,
                    'total': total
                })

            # Sort by total points (descending)
            player_data.sort(key=lambda x: x['total'], reverse=True)

            # Generate the image with the most recent completed GP
            image = await self._generate_points_table_image(player_data, all_gps, league_obj, most_recent_completed_gp)

            # Convert image to bytes
            img_bytes = BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            # Send as file
            file = discord.File(img_bytes, filename='points_table.png')
            await interaction.followup.send(file=file)

            BotLogger.log_command_success("points", interaction.user.name,
                                          f"Points table sent for league: {league_obj.name}")

        except Exception as e:
            BotLogger.log_command_error("points", interaction.user.name, e)
            raise

    async def _generate_points_table_image(self, player_data: List[dict], grand_prix_list: List,
                                           league_obj, most_recent_gp=None) -> Image.Image:
        """Generate a table image showing player standings with GP-by-GP scores"""

        # Constants
        TITLE_HEIGHT = 80
        CELL_HEIGHT = 40
        RANK_WIDTH = 60
        PLAYER_WIDTH = 200
        TEAM_WIDTH = 200
        GP_WIDTH = 80
        TOTAL_WIDTH = 100
        HEADER_HEIGHT = 40
        PADDING = 10

        num_gps = len(grand_prix_list)
        num_players = len(player_data)

        # Calculate image dimensions
        table_width = RANK_WIDTH + PLAYER_WIDTH + TEAM_WIDTH + (GP_WIDTH * num_gps) + TOTAL_WIDTH
        table_height = TITLE_HEIGHT + HEADER_HEIGHT + (CELL_HEIGHT * num_players)

        # Create image
        img = Image.new('RGB', (table_width, table_height), color=(3,3,3))
        draw = ImageDraw.Draw(img)

        # Try to load a font, fallback to default if not available
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/formulaone/f1-title.ttf", 24)
            font_header = ImageFont.truetype("/usr/share/fonts/truetype/formulaone/f1-desc-bold.ttf", 16)
            font_cell = ImageFont.truetype("/usr/share/fonts/truetype/formulaone/f1-desc-normal.ttf", 14)
        except:
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_cell = ImageFont.load_default()

        # Colors
        title_bg = (20, 20, 20)  # Dark background for title
        title_text = (255, 255, 255)
        header_bg = (232, 39, 42)  # F1 red
        header_text = (255, 255, 255)
        alt_row_bg = (10, 10, 10)
        grid_color = (3, 3, 3)
        text_color = (255, 255, 255)

        # Draw title section
        draw.rectangle([0, 0, table_width, TITLE_HEIGHT], fill=title_bg)

        # Determine title text
        if most_recent_gp:
            title_text_str = f"{league_obj.name} - After {most_recent_gp.event_name}"
        else:
            title_text_str = f"{league_obj.name} - Season Standings"

        draw.text((table_width // 2, TITLE_HEIGHT // 2), title_text_str,
                  fill=title_text, font=font_title, anchor="mm")

        # Draw header row (now offset by TITLE_HEIGHT)
        draw.rectangle([0, TITLE_HEIGHT, table_width, TITLE_HEIGHT + HEADER_HEIGHT], fill=header_bg)

        x_offset = 0

        # Header: Rank
        draw.text((x_offset + RANK_WIDTH // 2, TITLE_HEIGHT + HEADER_HEIGHT // 2), "Rank",
                  fill=header_text, font=font_header, anchor="mm")
        x_offset += RANK_WIDTH

        # Header: Player Name
        draw.text((x_offset + PLAYER_WIDTH // 2, TITLE_HEIGHT + HEADER_HEIGHT // 2), "Player Name",
                  fill=header_text, font=font_header, anchor="mm")
        x_offset += PLAYER_WIDTH

        # Header: Team Name
        draw.text((x_offset + TEAM_WIDTH // 2, TITLE_HEIGHT + HEADER_HEIGHT // 2), "Team Name",
                  fill=header_text, font=font_header, anchor="mm")
        x_offset += TEAM_WIDTH

        # Header: GP names (round numbers)
        for gp in grand_prix_list:
            draw.text((x_offset + GP_WIDTH // 2, TITLE_HEIGHT + HEADER_HEIGHT // 2), f"R{gp.round_number}",
                      fill=header_text, font=font_header, anchor="mm")
            x_offset += GP_WIDTH

        # Header: Total
        draw.text((x_offset + TOTAL_WIDTH // 2, TITLE_HEIGHT + HEADER_HEIGHT // 2), "Total",
                  fill=header_text, font=font_header, anchor="mm")

        # Draw data rows (now offset by TITLE_HEIGHT + HEADER_HEIGHT)
        y_offset = TITLE_HEIGHT + HEADER_HEIGHT
        for rank, player_info in enumerate(player_data, start=1):
            # Alternate row background
            if rank % 2 == 0:
                draw.rectangle([0, y_offset, table_width, y_offset + CELL_HEIGHT], fill=alt_row_bg)

            x_offset = 0

            # Rank
            draw.text((x_offset + RANK_WIDTH // 2, y_offset + CELL_HEIGHT // 2), str(rank),
                      fill=text_color, font=font_cell, anchor="mm")
            x_offset += RANK_WIDTH

            # Player Name (truncate if too long)
            player_name = player_info['player_name']
            if len(player_name) > 20:
                player_name = player_name[:17] + "..."
            draw.text((x_offset + PADDING, y_offset + CELL_HEIGHT // 2), player_name,
                      fill=text_color, font=font_cell, anchor="lm")
            x_offset += PLAYER_WIDTH

            # Team Name (truncate if too long)
            team_name = player_info['team_name']
            if len(team_name) > 20:
                team_name = team_name[:17] + "..."
            draw.text((x_offset + PADDING, y_offset + CELL_HEIGHT // 2), team_name,
                      fill=text_color, font=font_cell, anchor="lm")
            x_offset += TEAM_WIDTH

            # GP scores
            for gp in grand_prix_list:
                score = player_info['gp_scores'].get(gp.id, '-')
                score_text = str(score) if score != '-' else '-'
                draw.text((x_offset + GP_WIDTH // 2, y_offset + CELL_HEIGHT // 2), score_text,
                          fill=text_color, font=font_cell, anchor="mm")
                x_offset += GP_WIDTH

            # Total
            draw.text((x_offset + TOTAL_WIDTH // 2, y_offset + CELL_HEIGHT // 2), str(player_info['total']),
                      fill=text_color, font=font_cell, anchor="mm")

            y_offset += CELL_HEIGHT

        # Draw grid lines
        # Vertical lines
        x_offset = RANK_WIDTH
        for i in range(num_gps + 3):  # Player, Team, GPs, Total
            draw.line([x_offset, TITLE_HEIGHT, x_offset, table_height], fill=grid_color, width=1)
            if i < 2:
                x_offset += [PLAYER_WIDTH, TEAM_WIDTH][i]
            elif i < num_gps + 2:
                x_offset += GP_WIDTH
            else:
                x_offset += TOTAL_WIDTH

        # Horizontal lines
        y_offset = TITLE_HEIGHT + HEADER_HEIGHT
        for i in range(num_players + 1):
            draw.line([0, y_offset, table_width, y_offset], fill=grid_color, width=1)
            y_offset += CELL_HEIGHT

        return img

    @app_commands.command(name="points-breakdown", description="View detailed points breakdown for a Grand Prix")
    @app_commands.describe(
        league="Select the league",
        grand_prix="Select the Grand Prix",
        user="The user whose breakdown you want to view (leave blank for your own)"
    )
    @app_commands.autocomplete(league=league_autocomplete, grand_prix=grand_prix_autocomplete)
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def points_breakdown(
            self,
            interaction: discord.Interaction,
            league: str,
            grand_prix: str,
            user: discord.User = None
    ):
        target_user = user if user else interaction.user

        BotLogger.log_command_invocation(
            command_name="points-breakdown",
            user=interaction.user.name,
            user_id=interaction.user.id,
            league=league,
            guild_id=interaction.guild.id,
            target_user=target_user.name
        )
        """Display detailed points breakdown for a specific Grand Prix"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Get league
            league_obj: League = await self.league_repository.get_league_by_id(int(league))
            if not league_obj:
                BotLogger.log_command_error("points_breakdown", interaction.user.name,
                                            Exception(f"League not found for league ID: {league}"))
                await interaction.followup.send("League not found.", ephemeral=True)
                return

            # Get Grand Prix
            gp = await self.grand_prix_repository.get_grand_prix_by_id(int(grand_prix))
            if not gp:
                BotLogger.log_command_error("points_breakdown", interaction.user.name,
                                            Exception(f"Grand Prix not found for Grand Prix ID: {grand_prix}"))
                await interaction.followup.send("Grand Prix not found.", ephemeral=True)
                return

            # Get player from Discord user (target user, not necessarily the command invoker)
            player_obj = await self.player_repository.get_player_by_discord_id(target_user.id)
            if not player_obj:
                BotLogger.log_command_error("points_breakdown", interaction.user.name,
                                            Exception(f"Player not found for Discord ID: {target_user.id}"))
                if user is None:
                    await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
                else:
                    await interaction.followup.send(f"{target_user.display_name} is not registered.", ephemeral=True)
                return

            # Check if player is in this league
            is_in_league = await self.player_repository.is_player_in_league(player_obj.id, league_obj.id)
            if not is_in_league:
                BotLogger.log_command_error("points_breakdown", interaction.user.name,
                                            Exception(f"Player not found in league: {league_obj.name}"))
                if user is None:
                    await interaction.followup.send(f"You are not a member of **{league_obj.name}**.", ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"{target_user.display_name} is not a member of **{league_obj.name}**.", ephemeral=True)
                return

            # Get player's score for this GP
            score = await self.player_round_score_repository.get_score(player_obj.id, league_obj.id, gp.id)
            if not score:
                BotLogger.log_command_error("points_breakdown", interaction.user.name, Exception(
                    f"No score found for player {player_obj.name} in league {league_obj.name} for GP {gp.event_name}"))
                await interaction.followup.send(
                    f"No points data found for **{target_user.display_name}** in **{gp.event_name}** for **{league_obj.name}**.\n"
                    f"Points are calculated after the race is completed.",
                    ephemeral=True
                )
                return

            # Create embed with breakdown
            embed = await self._create_points_breakdown_embed(
                player_obj, league_obj, gp, score
            )

            BotLogger.log_command_success("points_breakdown", interaction.user.name,
                                          f"Points breakdown displayed for {player_obj.username} in {league_obj.name} for {gp.event_name}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            BotLogger.log_command_error("points_breakdown", interaction.user.name,
                                        Exception(f"Error displaying points breakdown: {e}"))
            await interaction.followup.send("An error occurred while retrieving the points breakdown.", ephemeral=True)

    async def _create_points_breakdown_embed(
            self,
            player_obj: Player,
            league_obj: League,
            grand_prix,
            score
    ) -> discord.Embed:
        """Create a formatted embed showing the points breakdown"""
        breakdown = score.breakdown_json

        # Create embed
        embed = discord.Embed(
            title=f"Points Breakdown - {grand_prix.event_name}",
            description=f"**Total Points: {breakdown.get('total', 0)}**",
            color=league_obj.embed_color,
            timestamp=score.calculated_at
        )

        # Driver 1
        if 'driver1' in breakdown:
            d1 = breakdown['driver1']
            embed.add_field(
                name=f"🏎️ Driver 1: {d1['name']}",
                value=f"**{d1['points']} points**\n{d1['details']}",
                inline=False
            )

        # Driver 2
        if 'driver2' in breakdown:
            d2 = breakdown['driver2']
            embed.add_field(
                name=f"🏎️ Driver 2: {d2['name']}",
                value=f"**{d2['points']} points**\n{d2['details']}",
                inline=False
            )

        # Driver 3
        if 'driver3' in breakdown:
            d3 = breakdown['driver3']
            embed.add_field(
                name=f"🏎️ Driver 3: {d3['name']}",
                value=f"**{d3['points']} points**\n{d3['details']}",
                inline=False
            )

        # Wildcard (Bogey Driver)
        if 'wildcard' in breakdown:
            wc = breakdown['wildcard']
            embed.add_field(
                name=f"🎲 Bogey Driver: {wc['name']}",
                value=f"**{wc['points']} points**\n{wc['details']}",
                inline=False
            )

        # Constructor
        if 'constructor' in breakdown:
            cons = breakdown['constructor']
            embed.add_field(
                name=f"🏁 Constructor: {cons['name']}",
                value=f"**{cons['points']} points**\n{cons['details']}",
                inline=False
            )

        # Set footer
        embed.set_footer(text=f"{player_obj.username} • {league_obj.name}")

        return embed

    @app_commands.describe(grand_prix='The grand prix you want to check deadlines for')
    @app_commands.autocomplete(grand_prix=grand_prix_autocomplete)
    @app_commands.command(name='check-deadlines', description='Check all relevant deadlines.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def check_deadlines(self, interaction: discord.Interaction, grand_prix: str = None):
        BotLogger.log_command_invocation(
            command_name="check-deadlines",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            grand_prix=grand_prix
        )

        await interaction.response.defer(ephemeral=True)

        try:
            season = await self.season_repository.get_active_season()

            if grand_prix is None:
                grand_prix_obj = await self.grand_prix_repository.get_next_grand_prix(season.id)
            else:
                grand_prix_obj = await self.grand_prix_repository.get_grand_prix_by_id(int(grand_prix))

            if not grand_prix_obj:
                BotLogger.log_command_error("check-deadlines", interaction.user.name,
                                            ValueError("Grand Prix not found"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("Grand Prix not found!"),
                    ephemeral=True
                )
                return

            deadlines_embed = discord.Embed(
                title=f'Deadlines for {grand_prix_obj.event_name}',
                description=f'',
                colour=13895688
            )

            player = await self.player_repository.get_player_by_discord_id(interaction.user.id)
            if player is None:
                BotLogger.log_command_error("check-deadlines", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(embed=await self.embedService.create_generic_failure_embed(
                    "You are not registered! Please use /register to sign up first."), ephemeral=True)
                return

            try:
                player_tz = pytz.timezone(player.timezone)
                draft_deadline_utc = grand_prix_obj.draft_deadline_utc
                counterpick_deadline_utc = grand_prix_obj.counterpick_deadline_utc

                draft_deadline_tz = draft_deadline_utc.astimezone(player_tz)
                counterpick_deadline_tz = counterpick_deadline_utc.astimezone(player_tz)

            except Exception as e:
                BotLogger.log_command_error("check-deadlines", interaction.user.name, e)
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(f"Failed to localize deadlines: {e}"),
                    ephemeral=True)
                return

            deadlines_embed.add_field(name="Draft Deadline", value=f"{draft_deadline_tz.strftime('%Y-%m-%d %I:%M %p')}")
            deadlines_embed.add_field(name="Counterpick Deadline",
                                      value=f"{counterpick_deadline_tz.strftime('%Y-%m-%d %I:%M %p')}")

            await interaction.followup.send(embed=deadlines_embed, ephemeral=True)

            BotLogger.log_command_success("check-deadlines", interaction.user.name,
                                          f"Deadlines displayed for {grand_prix_obj.event_name}")

        except Exception as e:
            BotLogger.log_command_error("check-deadlines", interaction.user.name, e)
            raise

    @app_commands.command(name='exhausted', description='Check your exhausted drivers.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def exhausted(self, interaction: discord.Interaction):
        BotLogger.log_command_invocation(
            command_name="exhausted",
            user=interaction.user.name,
            user_id=interaction.user.id,
            guild_id=interaction.guild_id
        )

        await interaction.response.defer(ephemeral=True)

        try:

            player: Optional[Player] = await self.player_repository.get_player_by_discord_id(interaction.user.id)

            if player is None:
                BotLogger.log_command_error("exhausted", interaction.user.name,
                                            ValueError("Player not registered"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered! Please use /register to sign up first."),
                    ephemeral=True)
                return

            player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(
                interaction.user.id)

            if not player_leagues:
                BotLogger.log_command_error("exhausted", interaction.user.name,
                                            ValueError("Player not in any leagues"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed("You are not in any leagues!"),
                    ephemeral=True)
                return

            # Filter to only leagues belonging to this guild
            guild_leagues: List[League] = await self.league_repository.get_leagues_by_discord_guild(
                interaction.guild_id)
            guild_league_ids = {league.id for league in guild_leagues}
            player_leagues = [league for league in player_leagues if league.id in guild_league_ids]

            if not player_leagues:
                BotLogger.log_command_error("exhausted", interaction.user.name,
                                            ValueError("Player not in any leagues in this guild"))
                await interaction.followup.send(
                    embed=await self.embedService.create_generic_failure_embed(
                        "You are not registered in any leagues in this server!"),
                    ephemeral=True)
                return

            embeds = []

            for league in player_leagues:
                exhausted_records = await self.exhaustion_repository.get_exhausted_drivers(
                    player_id=player.id,
                    league_id=league.id
                )

                league_embed = discord.Embed(
                    title="😴 Exhausted Drivers",
                    description=f"**League:** {league.name}",
                    color=discord.Color.from_rgb(
                        (league.embed_color >> 16) & 0xFF,
                        (league.embed_color >> 8) & 0xFF,
                        league.embed_color & 0xFF
                    )
                )

                if not exhausted_records:
                    league_embed.add_field(
                        name="No Exhausted Drivers",
                        value="You have no exhausted drivers in this league.",
                        inline=False
                    )
                else:
                    for record in exhausted_records:
                        driver = await self.driver_repository.get_driver_by_id(record.driver_id)
                        if driver:
                            league_embed.add_field(
                                name=f"{driver.first_name} {driver.last_name} ({driver.code})",
                                value=f"Used **{record.consecutive_uses}** consecutive race(s)",
                                inline=True
                            )

                embeds.append(league_embed)

            if len(embeds) == 1:
                embeds[0].set_footer(text=f"Requested by {interaction.user.display_name}",
                                     icon_url=interaction.user.display_avatar.url)
                await interaction.followup.send(embed=embeds[0], ephemeral=True)
            else:
                view = ExhaustedPaginationView(embeds, interaction.user)
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

            BotLogger.log_command_success("exhausted", interaction.user.name,
                                          f"Exhausted drivers displayed across {len(embeds)} league(s)")

        except Exception as e:
            BotLogger.log_command_error("exhausted", interaction.user.name, e)
            await interaction.followup.send(
                embed=await self.embedService.create_generic_failure_embed(f"An error occurred: {str(e)}"),
                ephemeral=True)


class TeamPaginationView(View):
    def __init__(self, embeds: List[discord.Embed], requester: discord.User):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.requester = requester

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Disable/enable buttons based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

        # Update the embed with page information
        page_label = f"Team {self.current_page + 1}"
        self.embeds[self.current_page].set_footer(
            text=f"{page_label} • Page {self.current_page + 1}/{self.total_pages} • Requested by {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class ProfilePaginationView(View):
    def __init__(self, embeds: List[discord.Embed], requester: discord.User):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.requester = requester

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Disable/enable buttons based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

        # Update the embed with page information
        page_type = "Overview" if self.current_page == 0 else f"League {self.current_page}"
        self.embeds[self.current_page].set_footer(
            text=f"{page_type} • Page {self.current_page + 1}/{self.total_pages} • Requested by {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class TimezonePaginationView(View):
    def __init__(self, embeds: List[discord.Embed]):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Disable/enable buttons based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

        # Update the embed with page information
        self.embeds[self.current_page].set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class CounterpickPaginationView(View):
    def __init__(self, embeds: List[discord.Embed], counterpick_data: List[dict], requester: discord.User, cog):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.counterpick_data = counterpick_data
        self.current_page = 0
        self.total_pages = len(embeds)
        self.requester = requester
        self.cog = cog  # Reference to FantasyUser cog for repository access

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Disable/enable buttons based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

        # Update the embed with page information
        self.embeds[self.current_page].set_footer(
            text=f"Counterpick {self.current_page + 1}/{self.total_pages} • Requested by {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


    @discord.ui.button(label="Cancel Counterpick", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        """Cancel the currently displayed counterpick"""
        await interaction.response.defer()

        try:
            # Get current counterpick data
            current_data = self.counterpick_data[self.current_page]
            cp = current_data['counterpick']
            gp = current_data['grand_prix']
            league = current_data['league']
            target_player = current_data['target_player']
            target_driver = current_data['target_driver']

            # Check if counterpick deadline has passed
            if gp.counterpick_deadline_utc:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if now > gp.counterpick_deadline_utc:
                    error_embed = await self.cog.embedService.create_generic_failure_embed(
                        f"Cannot cancel - counterpick deadline for {gp.event_name} has passed!"
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return

            # Delete the counterpick
            success = await self.cog.counterpick_repository.delete_counterpick(
                grand_prix_id=cp.grand_prix_id,
                league_id=cp.league_id,
                picking_player_id=cp.picking_player_id
            )

            if success:
                # Get updated remaining counterpicks
                remaining = await self.cog.counterpick_repository.get_remaining_counterpicks(
                    cp.picking_player_id, league.id, league.season_id
                )

                # Create public announcement embed
                public_embed = discord.Embed(
                    title="COUNTERPICK CANCELLATION",
                    description=f"**{gp.event_name}** (Round {gp.round_number})",
                    color=league.embed_color
                )

                public_embed.add_field(
                    name="🏹 Player",
                    value=self.requester.display_name,
                    inline=True
                )

                if target_player:
                    public_embed.add_field(
                        name="🎯 Previously Targeted",
                        value=target_player.username,
                        inline=True
                    )

                if target_driver:
                    public_embed.add_field(
                        name="🔓 Unbanned Driver",
                        value=f"{target_driver.first_name} {target_driver.last_name} ({target_driver.code})",
                        inline=True
                    )

                public_embed.add_field(
                    name="📊 Remaining Counterpicks",
                    value=f"{self.requester.display_name} now has {remaining} counterpicks left this season",
                    inline=False
                )

                public_embed.set_footer(text=f"League: {league.name}")

                # Send public announcement
                await interaction.channel.send(embed=public_embed)

                # Remove this counterpick from the view
                del self.embeds[self.current_page]
                del self.counterpick_data[self.current_page]
                self.total_pages -= 1

                if self.total_pages == 0:
                    # No more counterpicks
                    empty_embed = discord.Embed(
                        title="🎯 Your Active Counterpicks",
                        description="You don't have any active counterpicks for upcoming Grand Prix events.",
                        color=discord.Color.blue()
                    )
                    await interaction.edit_original_response(embed=empty_embed, view=None)
                else:
                    # Adjust current page if necessary
                    if self.current_page >= self.total_pages:
                        self.current_page = self.total_pages - 1

                    self.update_buttons()
                    await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)

            else:
                error_embed = await self.cog.embedService.create_generic_failure_embed(
                    "Failed to cancel counterpick. Please try again."
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)

        except Exception as e:
            error_embed = await self.cog.embedService.create_generic_failure_embed(
                f"An error occurred: {str(e)}"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class ExhaustedPaginationView(View):
    def __init__(self, embeds: List[discord.Embed], requester: discord.User):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.requester = requester

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

        self.embeds[self.current_page].set_footer(
            text=f"League {self.current_page + 1}/{self.total_pages} • Requested by {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))