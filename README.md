# F1-Fantasy-Manager

## A full stack application and Discord bot for running the LVS Formula 1 Fantasy League.

## Features  
## Multiple Ways to Play  
- F1 Fantasy Manager is accessible via both Discord commands as well as a custom Progressive Web App (PWA).

## Roadmap
- Implement basic Discord bot commands.
  - /draft
  - /team
  - /counterpick
  - /grand-prix
  - /check-deadline
  - /points
- Develop and test PWA functionality.
- Implement user authentication and authorization.

## TODO
- Implement Discord bot commands mentioned above.
- Populate driver, constructor and grands prix table data from FastF1/Jolpica API.
  - Use local data for the most part, only use API for data that is not available locally or to update data occasionally.
- Create PWA and admin console.
  - Admin controls
    - Create/edit/delete leagues
    - Update local driver, constructor and grands prix data by querying FastF1/Jolpica API.
    - Create/edit/delete user information.
    - Draft teams for users.
    - Assign users to leagues.
    - Calculate points for all leagues.
      - If a user forgets to draft a team, assign them a random team at the time of points calculation. Drivers should be assigned by weighted random, weighted by the drivers they drafted last. 