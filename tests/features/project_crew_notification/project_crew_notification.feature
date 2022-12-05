Feature: Project Crew Notification
  As a user,
  I want to be notified project crew member updates.

  Scenario: Twoflower is added as an editor to a project
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Vetinari adds twoflower as an editor
    Then Twoflower gets notified 'You were made an editor of Expo 2010 by Vetinari'
    Then Rincewind gets notified 'Twoflower was made an editor of Expo 2010 by Vetinari'
