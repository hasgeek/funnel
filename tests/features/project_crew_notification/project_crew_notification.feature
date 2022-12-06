Feature: Project Crew Notification
  As a user,
  I want to be notified project crew member updates.

  Scenario Outline: Twoflower is added as an editor to a project
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Vetinari adds twoflower as an editor
    Then <user> gets notified <notification_string>.

    Examples:
      | user      | notification_string                                             |
      | Twoflower | Havelock Vetinari made you an editor of Ankh-Morpork 2010       |
      | Rincewind | Havelock Vetinari made Twoflower an editor of Ankh-Morpork 2010 |
