The website is no longer available.

# Dodge-Or-Not-
- A League of Legends Dodge Tool
- This repo contains a modified version of the program I used to gather information for my website ~~dodgeornot.herokuapp~~ (The website is no longer supported)
- You can view an example of DodgeOrNot in action here: https://www.youtube.com/watch?v=Hhp5ifnRIn4

 What is DodgeOrNot?

- DodgeOrNot is a stats tool designed to make it easier for people to get information about teammates while in champ select. Unfortunately Riot Games did not approve my application for a product key so I won't make the application public. However, I am posting this so that someone else who has a better idea might learn something about accessing riots api and manipulating the data in python.
  
How does it work?

- The program gathers data using Riots API and the python library cassiopeia(https://github.com/meraki-analytics/cassiopeia). Next, it modifies and stores the information in python dictionaries which are later converted to pandas dataframs and styled. One extremely important library is roleml(https://github.com/Canisback/roleML) which classifies summoner roles far more accurately than the information provided through riots API.
