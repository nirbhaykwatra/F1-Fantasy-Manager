from typing import List, Optional
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ui import View, Button
from discord.ext import commands
from src.f1bot.config import load_config
from src.f1bot.services.models import (
    PlayerRepository,
    Player,
    LeagueRepository,
    League,
    DraftRepository,
    PlayerLeague,
    Draft,
    GrandPrixRepository,
    DriverRepository,
    ConstructorRepository
)
import zoneinfo

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

    async def league_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        """Autocomplete callback for league choices"""
        return await self.bot.choiceService.get_league_choices(interaction.guild_id)

    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to join', timezone='Your local timezone. Use /timezones to show a list of available timezones. Copy the timezone name exactly as it appears in the list.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def register(self, interaction: discord.Interaction, league: str, team_name: str, team_motto: str, timezone: str):
        print(f'Register command invoked with league id {int(league)}, team: {team_name}, motto: {team_motto}')

        # If entered timezone is invalid, send error message and return
        if timezone not in zoneinfo.available_timezones():
            await interaction.response.send_message(f'Invalid timezone! Please use /timezones to see a list of available timezones.', ephemeral=True)
            return

        # Search for league by id
        league_id = int(league)
        league_object: League | None = await self.league_repository.get_league_by_id(league_id)

        # If no league is found, send error message and return
        if league_object is None:
            await interaction.response.send_message(f'League with id {league_id} not found!', ephemeral=True)
            return

        # Get list of leagues the user is registered in
        player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)

        # If user is already registered for league, send error message and return
        if league_object in player_leagues:
            await interaction.response.send_message(f'You are already registered for {league_object.name}!', ephemeral=True)
            return

        # Search for player by discord id
        player_if_exists = await self.player_repository.get_player_by_discord_id(interaction.user.id)

        # If player is already in the database, just add them to the selected league and send success message
        if player_if_exists:
            await self.player_repository.add_player_to_league(league_id=league_id, player_id=player_if_exists.id, team_name=team_name, team_motto=team_motto)
            await interaction.response.send_message(f'Successfully registered for {league_object.name}!', ephemeral=True)
            return

        # If player is not in the database, create a new player and add them to the selected league
        created_player = await self.player_repository.create_player(
            discord_user_id=interaction.user.id,
            username=interaction.user.name,
            timezone=timezone,
        )
        player_league = await self.player_repository.add_player_to_league(league_id=league_id, player_id=created_player.id, team_name=team_name, team_motto=team_motto)

        # If player was successfully registered, send success message
        if created_player and player_league is not None:
            await interaction.response.send_message(f'Successfully registered for {league_object.name}!', ephemeral=True)
        else:
            await interaction.response.send_message(f'Failed to register for {league_object.name}. Please check your input options and try again.', ephemeral=True)

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='unregister', description='Unregister from a league!')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to unregister from')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def unregister(self, interaction: discord.Interaction, league: str):
        print(f'Unregister command invoked with league id {int(league)}')

        # Search for league by id
        league_id = int(league)
        league_object: League | None = await self.league_repository.get_league_by_id(league_id)
        # If no league is found, send error message and return
        if league_object is None:
            await interaction.response.send_message(f'League with id {league_id} not found!', ephemeral=True)
            return
        # Get player leagues by Discord ID
        player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(interaction.user.id)
        # If user is not registered for league, send error message and return
        if league_object not in player_leagues:
            await interaction.response.send_message(f'You are not registered in {league_object.name}!', ephemeral=True)
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
            await interaction.response.send_message(f'You are no longer registered in any leagues!', ephemeral=True)
            return
        else:
            await interaction.response.send_message(f'Successfully unregistered from {league_object.name}!', ephemeral=True)

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='draft', description='Draft your team for the selected round!')
    # @app_commands.autocomplete(driver1=driver_autocomplete, driver2=driver_autocomplete, driver3=driver_autocomplete, bogey=bogey_autocomplete, team=team_autocomplete)
    @app_commands.describe(
        league='The league you want to draft for',
        driver1='The first driver you want to draft',
        driver2='The second driver you want to draft',
        driver3='The third driver you want to draft',
        bogey='The bogey driver you want to draft',
        team='The constructor you want to draft'
    )
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def draft(self, interaction: discord.Interaction, league: str, driver1: str, driver2: str, driver3: str, bogey: str, team: str):
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='profile', description="View yours or another user's profile!")
    @app_commands.describe(user='The user you want to view. Leave blank to view your own profile.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        print(f"Profile command invoked with user: {user.display_name if user else interaction.user.display_name}")
        target_user = user if user else interaction.user
        print(f"Profile command invoked with user: {target_user.display_name}")
        await interaction.response.defer(ephemeral=True)

        player: Optional[Player] = await self.player_repository.get_player_by_discord_id(discord_user_id=target_user.id)

        if player is None:
            if user is None:
                await interaction.followup.send(f'You are not registered in any leagues!', ephemeral=True)
            else:
                await interaction.followup.send(f'The selected user is not registered in any leagues!', ephemeral=True)
            return

        # Get all leagues the player is in
        player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(target_user.id)

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

                # Get current draft if there's an active/upcoming GP
                if next_gp:
                    current_draft: Optional[Draft] = await self.draft_repository.get_draft(
                        player_id=player.id,
                        league_id=league.id,
                        grand_prix_id=next_gp.id
                    )

                    if current_draft:
                        # Get driver names for the draft
                        driver1 = await self.driver_repository.get_driver_by_id(current_draft.driver1_id)
                        driver2 = await self.driver_repository.get_driver_by_id(current_draft.driver2_id)
                        driver3 = await self.driver_repository.get_driver_by_id(current_draft.driver3_id)
                        wildcard = await self.driver_repository.get_driver_by_id(current_draft.wildcard_id)
                        constructor = await self.constructor_repository.get_constructor_by_id(
                            current_draft.constructor_id)

                        draft_info = f"**Round {next_gp.round_number}: {next_gp.event_name}**\n"
                        if driver1:
                            draft_info += f"Driver 1: {driver1.first_name} {driver1.last_name}\n"
                        if driver2:
                            draft_info += f"Driver 2: {driver2.first_name} {driver2.last_name}\n"
                        if driver3:
                            draft_info += f"Driver 3: {driver3.first_name} {driver3.last_name}\n"
                        if wildcard:
                            draft_info += f"Bogey: {wildcard.first_name} {wildcard.last_name}\n"
                        if constructor:
                            draft_info += f"Constructor: {constructor.full_name}"

                        league_embed.add_field(name="Current Draft", value=draft_info, inline=False)
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

    @app_commands.command(name='timezones', description='List all available timezones.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def timezones(self, interaction: discord.Interaction):
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
                                              description="Here is a list of all available timezones:",
                                              color=discord.Color.blurple())
                fields = 0

        # Add the last embed if it has any fields
        if fields > 0:
            embeds.append(current_embed)

        # Create pagination view
        view = TimezonePaginationView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

    # For the following commands, try out using discord ui instead of simple embeds.
    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='team', description='View your team.')
    @app_commands.describe(user='The user you want to view. Leave blank to view your own team.')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def team(self, interaction: discord.Interaction, user: discord.User = None):
        target_user = user if user else interaction.user
        print(f"Team command invoked with user: {target_user.display_name}")
        await interaction.response.defer(ephemeral=True)

        player: Optional[Player] = await self.player_repository.get_player_by_discord_id(discord_user_id=target_user.id)

        if player is None:
            if user is None:
                await interaction.followup.send(f'You are not registered in any leagues!', ephemeral=True)
            else:
                await interaction.followup.send(f'The selected user is not registered in any leagues!', ephemeral=True)
            return

        # Get all leagues the player is in
        player_leagues: List[League] = await self.player_repository.get_leagues_for_player_by_discord_id(target_user.id)

        if len(player_leagues) == 0:
            await interaction.followup.send(
                f'{"You are" if user is None else f"{target_user.display_name} is"} not registered in any leagues!',
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

            # Get and display CURRENT draft (next GP)
            if next_gp:
                current_draft: Optional[Draft] = await self.draft_repository.get_draft(
                    player_id=player.id,
                    league_id=league.id,
                    grand_prix_id=next_gp.id
                )

                if current_draft:
                    driver1 = await self.driver_repository.get_driver_by_id(current_draft.driver1_id)
                    driver2 = await self.driver_repository.get_driver_by_id(current_draft.driver2_id)
                    driver3 = await self.driver_repository.get_driver_by_id(current_draft.driver3_id)
                    wildcard = await self.driver_repository.get_driver_by_id(current_draft.wildcard_id)
                    constructor = await self.constructor_repository.get_constructor_by_id(current_draft.constructor_id)

                    draft_info = f"**Round {next_gp.round_number}: {next_gp.event_name}**\n"
                    if driver1:
                        draft_info += f"Driver 1: {driver1.first_name} {driver1.last_name}\n"
                    if driver2:
                        draft_info += f"Driver 2: {driver2.first_name} {driver2.last_name}\n"
                    if driver3:
                        draft_info += f"Driver 3: {driver3.first_name} {driver3.last_name}\n"
                    if wildcard:
                        draft_info += f"Bogey: {wildcard.first_name} {wildcard.last_name}\n"
                    if constructor:
                        draft_info += f"Constructor: {constructor.full_name}"

                    league_embed.add_field(name="Current Draft", value=draft_info, inline=False)
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

                    prev_draft_info = f"**Round {prev_gp.round_number}: {prev_gp.event_name}**\n"
                    if prev_driver1:
                        prev_draft_info += f"Driver 1: {prev_driver1.first_name} {prev_driver1.last_name}\n"
                    if prev_driver2:
                        prev_draft_info += f"Driver 2: {prev_driver2.first_name} {prev_driver2.last_name}\n"
                    if prev_driver3:
                        prev_draft_info += f"Driver 3: {prev_driver3.first_name} {prev_driver3.last_name}\n"
                    if prev_wildcard:
                        prev_draft_info += f"Bogey: {prev_wildcard.first_name} {prev_wildcard.last_name}\n"
                    if prev_constructor:
                        prev_draft_info += f"Constructor: {prev_constructor.full_name}"

                    league_embed.add_field(name="Previous Draft", value=prev_draft_info, inline=False)
                else:
                    league_embed.add_field(
                        name="Previous Draft",
                        value=f"No draft submitted for {prev_gp.event_name}",
                        inline=False
                    )
            else:
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

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='counterpick', description='Counterpick another player for the selected round in your league.')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The league you want to counterpick in', user='The user you want to counterpick against', driver='The driver you want to counterpick')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def counterpick(self, interaction: discord.Interaction, league: str, user: discord.User, driver: str):
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='grand-prix', description='View the details of a specific grand prix.')
    # @app_commands.autocomplete(grand_prix=grand_prix_autocomplete)
    @app_commands.describe(grand_prix='The grand prix you want to view')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def grand_prix(self, interaction: discord.Interaction, grand_prix: str):
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

    @app_commands.checks.has_any_role("Administrator", "F1 Fantasy Player")
    @app_commands.command(name='points', description='View the current points table for the selected league.')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.describe(league='The grand prix you want to view')
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def points(self, interaction: discord.Interaction, league: str):
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))