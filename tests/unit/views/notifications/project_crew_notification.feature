Feature: Project Crew Notification
  As a user,
  I want to be notified project crew member updates.

  Scenario Outline: Ridcully is added to a project
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    When Vetinari adds Ridcully with role <role> to Ankh-Morpork 2010 project
    Then <user> gets notified <notification_string> about addition.

    Examples:
      | user     | role            | notification_string                                                                 |
      | Ridcully | editor          | Havelock Vetinari made you an editor of Ankh-Morpork 2010                           |
      | Vimes    | editor          | Havelock Vetinari made Mustrum Ridcully an editor of Ankh-Morpork 2010              |
      | Vetinari | editor          | Havelock Vetinari made Mustrum Ridcully an editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | Havelock Vetinari made you a promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Havelock Vetinari made Mustrum Ridcully a promoter of Ankh-Morpork 2010             |
      | Vetinari | promoter        | Havelock Vetinari made Mustrum Ridcully a promoter of Ankh-Morpork 2010             |
      | Ridcully | editor,promoter | Havelock Vetinari made you an editor and promoter of Ankh-Morpork 2010              |
      | Vimes    | editor,promoter | Havelock Vetinari made Mustrum Ridcully an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | editor,promoter | Havelock Vetinari made Mustrum Ridcully an editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | Havelock Vetinari added you to the crew of Ankh-Morpork 2010                        |
      | Vimes    | usher           | Havelock Vetinari added Mustrum Ridcully to the crew of Ankh-Morpork 2010           |
      | Vetinari | usher           | Havelock Vetinari added Mustrum Ridcully to the crew of Ankh-Morpork 2010           |

  Scenario Outline: Vetinari has invited Ridcully
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    When Vetinari invites Ridcully with a role <role> to Ankh-Morpork 2010 project
    Then <user> gets notified <notification_string> about invitation.

    Examples:
      | user     | role            | notification_string                                                                                      |
      | Ridcully | editor          | You have been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari                          |
      | Vimes    | editor          | Mustrum Ridcully has been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Vetinari | editor          | Mustrum Ridcully has been invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Ridcully | promoter        | You have been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari                         |
      | Vimes    | promoter        | Mustrum Ridcully has been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vetinari | promoter        | Mustrum Ridcully has been invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Ridcully | editor,promoter | You have been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vimes    | editor,promoter | Mustrum Ridcully has been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Vetinari | editor,promoter | Mustrum Ridcully has been invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Ridcully | usher           | You have been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari                         |
      | Vimes    | usher           | Mustrum Ridcully has been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vetinari | usher           | Mustrum Ridcully has been invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari             |

  Scenario Outline: Ridcully has accepted the invite
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    When Ridcully accepts the invitation to be a member of Ankh-Morpork 2010 project with a role <role>
    Then <user> gets notified <notification_string> about acceptance.

    Examples:
      | user     | role            | notification_string                                                                    |
      | Ridcully | editor          | You have accepted an invite to join the crew of Ankh-Morpork 2010                      |
      | Vimes    | editor          | Mustrum Ridcully has accepted an invite to be editor of Ankh-Morpork 2010              |
      | Vetinari | editor          | Mustrum Ridcully has accepted an invite to be editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | You have accepted an invite to join the crew of Ankh-Morpork 2010                      |
      | Vimes    | promoter        | Mustrum Ridcully has accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Vetinari | promoter        | Mustrum Ridcully has accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Ridcully | editor,promoter | You have accepted an invite to join the crew of Ankh-Morpork 2010                      |
      | Vimes    | editor,promoter | Mustrum Ridcully has accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | editor,promoter | Mustrum Ridcully has accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | You have accepted an invite to join the crew of Ankh-Morpork 2010                      |
      | Vimes    | usher           | Mustrum Ridcully has accepted an invite to join the crew of Ankh-Morpork 2010          |
      | Vetinari | usher           | Mustrum Ridcully has accepted an invite to join the crew of Ankh-Morpork 2010          |

  Scenario Outline: Ridcully has changed the role
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    When Ridcully's role changes to <role> in Ankh-Morpork 2010 project
    Then <user> gets notified <notification_string> about amendment.

    Examples:
      | user     | role            | notification_string                                                                    |
      | Ridcully | editor          | You have changed your role to an editor of Ankh-Morpork 2010                           |
      | Vimes    | editor          | Mustrum Ridcully has changed their role to an editor of Ankh-Morpork 2010              |
      | Vetinari | editor          | Mustrum Ridcully has changed their role to an editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | You have changed your role to a promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Mustrum Ridcully has changed their role to a promoter of Ankh-Morpork 2010             |
      | Vetinari | promoter        | Mustrum Ridcully has changed their role to a promoter of Ankh-Morpork 2010             |
      | Ridcully | editor,promoter | You are now an editor and promoter of Ankh-Morpork 2010                                |
      | Vimes    | editor,promoter | Mustrum Ridcully has changed their role to an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | editor,promoter | Mustrum Ridcully has changed their role to an editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | You have changed your role to be a crew of Ankh-Morpork 2010                           |
      | Vimes    | usher           | Mustrum Ridcully has changed their role to be a crew of Ankh-Morpork 2010              |
      | Vetinari | usher           | Mustrum Ridcully has changed their role to be a crew of Ankh-Morpork 2010              |

  Scenario Outline: Ridcully is removed by Vimes
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    Given Ridcully is a crew member of the project
    When Ridcully is removed from the project by Vimes
    Then Ridcully gets a notification 'You were removed as crew member of Ankh-Morpork 2010 by Havelock Vetinari'
    Then Crew members get a notification 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Havelock Vetinari'

  Scenario Outline: Ridcully removes himself
    Given Vetinari is an owner of the Ankh-Morpork organization
    Given Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    Given Vimes is a promoter of Ankh-Morpork 2010
    Given Ridcully is a crew member of the project
    When Ridcully removes himself from the project
    Then Ridcully gets a notification 'You removed yourself as a crew member of Ankh-Morpork 2010'
    Then Crew members get a notification 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Havelock Vetinari'
