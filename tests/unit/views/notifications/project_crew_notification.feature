Feature: Project Crew Notification
  As a user,
  I want to be notified project crew member updates.

  Scenario Outline: Twoflower is added to a project
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Vetinari adds twoflower with role <role>
    Then <user> gets notified <notification_string> about addition.

    Examples:
      | user      | role            | notification_string                                                          |
      | Twoflower | editor          | Havelock Vetinari made you an editor of Ankh-Morpork 2010                    |
      | Rincewind | editor          | Havelock Vetinari made Twoflower an editor of Ankh-Morpork 2010              |
      | Vetinari  | editor          | Havelock Vetinari made Twoflower an editor of Ankh-Morpork 2010              |
      | Twoflower | promoter        | Havelock Vetinari made you a promoter of Ankh-Morpork 2010                   |
      | Rincewind | promoter        | Havelock Vetinari made Twoflower a promoter of Ankh-Morpork 2010             |
      | Vetinari  | promoter        | Havelock Vetinari made Twoflower a promoter of Ankh-Morpork 2010             |
      | Twoflower | editor,promoter | Havelock Vetinari made you an editor and promoter of Ankh-Morpork 2010       |
      | Rincewind | editor,promoter | Havelock Vetinari made Twoflower an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari  | editor,promoter | Havelock Vetinari made Twoflower an editor and promoter of Ankh-Morpork 2010 |
      | Twoflower | crew            | Havelock Vetinari added you to the crew of Ankh-Morpork 2010                 |
      | Rincewind | crew            | Havelock Vetinari added Twoflower to the crew of Ankh-Morpork 2010           |
      | Vetinari  | crew            | Havelock Vetinari added Twoflower to the crew of Ankh-Morpork 2010           |

  Scenario Outline: Vetinari has invited Twoflower
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Vetinari invites Twoflower to the project with a role <role>
    Then <user> gets notified <notification_string> about invitation.

    Examples:
      | user      | role            | notification_string                                                                               |
      | Twoflower | editor          | You have been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari                   |
      | Rincewind | editor          | Twoflower has been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Vetinari  | editor          | Twoflower has been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Twoflower | promoter        | You have been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari                  |
      | Rincewind | promoter        | Twoflower has been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vetinari  | promoter        | Twoflower has been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Twoflower | editor,promoter | You have been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari      |
      | Rincewind | editor,promoter | Twoflower has been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Vetinari  | editor,promoter | Twoflower has been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Twoflower | crew            | You have been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari                  |
      | Rincewind | crew            | Twoflower has been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vetinari  | crew            | Twoflower has been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari             |

  Scenario Outline: Twoflower has accepted the invite
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Twoflower accepts the invitation to be an editor of project Expo 2010 with a role <role>
    Then <user> gets notified <notification_string> about acceptance.

    Examples:
      | user      | role            | notification_string                                                             |
      | Twoflower | editor          | You have accepted an invite to join the crew of Ankh-Morpork 2010               |
      | Rincewind | editor          | Twoflower has accepted an invite to be editor of Ankh-Morpork 2010              |
      | Vetinari  | editor          | Twoflower has accepted an invite to be editor of Ankh-Morpork 2010              |
      | Twoflower | promoter        | You have accepted an invite to join the crew of Ankh-Morpork 2010               |
      | Rincewind | promoter        | Twoflower has accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Vetinari  | promoter        | Twoflower has accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Twoflower | editor,promoter | You have accepted an invite to join the crew of Ankh-Morpork 2010               |
      | Rincewind | editor,promoter | Twoflower has accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Vetinari  | editor,promoter | Twoflower has accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Twoflower | crew            | You have accepted an invite to join the crew of Ankh-Morpork 2010               |
      | Rincewind | crew            | Twoflower has accepted an invite to join the crew of Ankh-Morpork 2010          |
      | Vetinari  | crew            | Twoflower has accepted an invite to join the crew of Ankh-Morpork 2010          |

  Scenario Outline: Twoflower has changed the role
    Given Rincewind and Twoflower are project crew in the project Expo 2010
    When Twoflower's role changes to <role>
    Then <user> gets notified <notification_string> about amendment.

    Examples:
      | user      | role            | notification_string                                                             |
      | Twoflower | editor          | You have changed your role to an editor of Ankh-Morpork 2010                    |
      | Rincewind | editor          | Twoflower has changed their role to an editor of Ankh-Morpork 2010              |
      | Vetinari  | editor          | Twoflower has changed their role to an editor of Ankh-Morpork 2010              |
      | Twoflower | promoter        | You have changed your role to a promoter of Ankh-Morpork 2010                   |
      | Rincewind | promoter        | Twoflower has changed their role to a promoter of Ankh-Morpork 2010             |
      | Vetinari  | promoter        | Twoflower has changed their role to a promoter of Ankh-Morpork 2010             |
      | Twoflower | editor,promoter | You are now an editor and promoter of Ankh-Morpork 2010                         |
      | Rincewind | editor,promoter | Twoflower has changed their role to an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari  | editor,promoter | Twoflower has changed their role to an editor and promoter of Ankh-Morpork 2010 |
      | Twoflower | crew            | You have changed your role to be a crew of Ankh-Morpork 2010                    |
      | Rincewind | crew            | Twoflower has changed their role to be a crew of Ankh-Morpork 2010              |
      | Vetinari  | crew            | Twoflower has changed their role to be a crew of Ankh-Morpork 2010              |
