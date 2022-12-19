Feature: Project Crew Notification
  As a project crew member, I want to be notified of changes to the crew, with a message
  telling me exactly what has changed and who did it

  Background:
    Given Vetinari is an owner of the Ankh-Morpork organization
    And Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    And Vimes is a promoter of the Ankh-Morpork 2010 project

  Scenario Outline: Ridcully is added to a project
    When Vetinari adds Ridcully with role <role> to the Ankh-Morpork 2010 project
    Then <user> gets notified with <notification_string> about the addition

    Examples:
      | user     | role            | notification_string                                                                 |
      | Vetinari | editor          | You made Mustrum Ridcully an editor of Ankh-Morpork 2010                            |
      | Ridcully | editor          | Havelock Vetinari made you an editor of Ankh-Morpork 2010                           |
      | Vimes    | editor          | Havelock Vetinari made Mustrum Ridcully an editor of Ankh-Morpork 2010              |
      | Vetinari | promoter        | You made Mustrum Ridcully a promoter of Ankh-Morpork 2010                           |
      | Ridcully | promoter        | Havelock Vetinari made you a promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Havelock Vetinari made Mustrum Ridcully a promoter of Ankh-Morpork 2010             |
      | Vetinari | editor,promoter | You made Mustrum Ridcully an editor and promoter of Ankh-Morpork 2010               |
      | Ridcully | editor,promoter | Havelock Vetinari made you an editor and promoter of Ankh-Morpork 2010              |
      | Vimes    | editor,promoter | Havelock Vetinari made Mustrum Ridcully an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | usher           | You added Mustrum Ridcully to the crew of Ankh-Morpork 2010                         |
      | Ridcully | usher           | Havelock Vetinari added you to the crew of Ankh-Morpork 2010                        |
      | Vimes    | usher           | Havelock Vetinari added Mustrum Ridcully to the crew of Ankh-Morpork 2010           |

  Scenario Outline: Vetinari invites Ridcully
    When Vetinari invites Ridcully with role <role> to the Ankh-Morpork 2010 project
    Then <user> gets notified with <notification_string> about the invitation

    Examples:
      | user     | role            | notification_string                                                                          |
      | Vetinari | editor          | You invited Mustrum Ridcully to be an editor of Ankh-Morpork 2010                            |
      | Ridcully | editor          | Havelock Vetinari invited you to be an editor of Ankh-Morpork 2010                           |
      | Vimes    | editor          | Havelock Vetinari invited Mustrum Ridcully to be an editor of Ankh-Morpork 2010              |
      | Vetinari | promoter        | You invited Mustrum Ridcully to be a promoter of Ankh-Morpork 2010                           |
      | Ridcully | promoter        | Havelock Vetinari invited you to be a promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Havelock Vetinari invited Mustrum Ridcully to be a promoter of Ankh-Morpork 2010             |
      | Vetinari | editor,promoter | You invited Mustrum Ridcully to be an editor and promoter of Ankh-Morpork 2010               |
      | Ridcully | editor,promoter | Havelock Vetinari invited you to be an editor and promoter of Ankh-Morpork 2010              |
      | Vimes    | editor,promoter | Havelock Vetinari invited Mustrum Ridcully to be an editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | usher           | You invited Mustrum Ridcully to join the crew of Ankh-Morpork 2010                           |
      | Ridcully | usher           | Havelock Vetinari invited you to join the crew of Ankh-Morpork 2010                          |
      | Vimes    | usher           | Havelock Vetinari invited Mustrum Ridcully to join the crew of Ankh-Morpork 2010             |

  Scenario Outline: Ridcully accepted the invite
    Given Vetinari invited Ridcully with role <role> to the Ankh-Morpork 2010 project
    When Ridcully accepts the invitation to be a crew member of the Ankh-Morpork 2010 project
    Then <user> gets notified with <notification_string> about the acceptance

    Examples:
      | user     | role            | notification_string                                                                |
      | Ridcully | editor          | You accepted an invite to be editor of Ankh-Morpork 2010                           |
      | Vetinari | editor          | Mustrum Ridcully accepted an invite to be editor of Ankh-Morpork 2010              |
      | Vimes    | editor          | Mustrum Ridcully accepted an invite to be editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | You accepted an invite to be promoter of Ankh-Morpork 2010                         |
      | Vetinari | promoter        | Mustrum Ridcully accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Vimes    | promoter        | Mustrum Ridcully accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Ridcully | editor,promoter | You accepted an invite to be editor and promoter of Ankh-Morpork 2010              |
      | Vetinari | editor,promoter | Mustrum Ridcully accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Vimes    | editor,promoter | Mustrum Ridcully accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | You accepted an invite to join the crew of Ankh-Morpork 2010                       |
      | Vetinari | usher           | Mustrum Ridcully accepted an invite to join the crew of Ankh-Morpork 2010          |
      | Vimes    | usher           | Mustrum Ridcully accepted an invite to join the crew of Ankh-Morpork 2010          |

  Scenario Outline: Vetinari changes Ridcully's role
    Given Ridcully is an existing crew member with roles editor, promoter and usher of the Ankh-Morpork 2010 project
    When Vetinari changes Ridcully's role to <role> in the Ankh-Morpork 2010 project
    Then <user> gets notified with <notification_string> about the change

    Examples:
      | user     | role            | notification_string                                                                           |
      | Vetinari | editor          | You changed Mustrum Ridcully's role to editor of Ankh-Morpork 2010                            |
      | Ridcully | editor          | Havelock Vetinari changed your role to editor of Ankh-Morpork 2010                            |
      | Vimes    | editor          | Havelock Vetinari changed Mustrum Ridcully's role to editor of Ankh-Morpork 2010              |
      | Vetinari | promoter        | You changed Mustrum Ridcully's role to promoter of Ankh-Morpork 2010                          |
      | Ridcully | promoter        | Havelock Vetinari changed your role to promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Havelock Vetinari changed Mustrum Ridcully's role to promoter of Ankh-Morpork 2010            |
      | Vetinari | editor,promoter | You changed Mustrum Ridcully's role to editor and promoter of Ankh-Morpork 2010               |
      | Ridcully | editor,promoter | Havelock Vetinari changed your role to editor and promoter of Ankh-Morpork 2010               |
      | Vimes    | editor,promoter | Havelock Vetinari changed Mustrum Ridcully's role to editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | usher           | You changed Mustrum Ridcully's role to crew member of Ankh-Morpork 2010                       |
      | Ridcully | usher           | Havelock Vetinari changed your role to crew member of Ankh-Morpork 2010                       |
      | Vimes    | usher           | Havelock Vetinari changed Mustrum Ridcully's role to crew member of Ankh-Morpork 2010         |

  Scenario Outline: Ridcully changed their own role
    Given Vetinari made Ridcully an admin of Ankh-Morpork
    And Ridcully is an existing crew member with roles editor, promoter and usher of the Ankh-Morpork 2010 project
    When Ridcully changes their role to <role> in the Ankh-Morpork 2010 project
    Then <user> gets notified with <notification_string> about the change

    Examples:
      | user     | role            | notification_string                                                             |
      | Ridcully | editor          | You changed your role to editor of Ankh-Morpork 2010                            |
      | Vimes    | editor          | Mustrum Ridcully changed their role to editor of Ankh-Morpork 2010              |
      | Vetinari | editor          | Mustrum Ridcully changed their role to editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | You changed your role to promoter of Ankh-Morpork 2010                          |
      | Vimes    | promoter        | Mustrum Ridcully changed their role to promoter of Ankh-Morpork 2010            |
      | Vetinari | promoter        | Mustrum Ridcully changed their role to promoter of Ankh-Morpork 2010            |
      | Ridcully | editor,promoter | You are now editor and promoter of Ankh-Morpork 2010                            |
      | Vimes    | editor,promoter | Mustrum Ridcully changed their role to editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | editor,promoter | Mustrum Ridcully changed their role to editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | You changed your role to crew member of Ankh-Morpork 2010                       |
      | Vimes    | usher           | Mustrum Ridcully changed their role to crew member of Ankh-Morpork 2010         |
      | Vetinari | usher           | Mustrum Ridcully changed their role to crew member of Ankh-Morpork 2010         |

  Scenario Outline: Vetinari removes Ridcully
    Given Ridcully is an existing crew member of the Ankh-Morpork 2010 project with role <role>
    When Vetinari removes Ridcully from the Ankh-Morpork 2010 project crew
    Then <user> is notified of the removal with <notification_string>

    Examples:
      | user     | role            | notification_string                                                                      |
      | Vetinari | editor          | You removed Mustrum Ridcully from editor of Ankh-Morpork 2010                            |
      | Ridcully | editor          | Havelock Vetinari removed you from editor of Ankh-Morpork 2010                           |
      | Vimes    | editor          | Havelock Vetinari removed Mustrum Ridcully from editor of Ankh-Morpork 2010              |
      | Vetinari | promoter        | You removed Mustrum Ridcully from promoter of Ankh-Morpork 2010                          |
      | Ridcully | promoter        | Havelock Vetinari removed you from promoter of Ankh-Morpork 2010                         |
      | Vimes    | promoter        | Havelock Vetinari removed Mustrum Ridcully from promoter of Ankh-Morpork 2010            |
      | Vetinari | editor,promoter | You removed Mustrum Ridcully from editor and promoter of Ankh-Morpork 2010               |
      | Ridcully | editor,promoter | Havelock Vetinari removed you from editor and promoter of Ankh-Morpork 2010              |
      | Vimes    | editor,promoter | Havelock Vetinari removed Mustrum Ridcully from editor and promoter of Ankh-Morpork 2010 |
      | Vetinari | usher           | You removed Mustrum Ridcully from the crew of Ankh-Morpork 2010                          |
      | Ridcully | usher           | Havelock Vetinari removed you from the crew of Ankh-Morpork 2010                         |
      | Vimes    | usher           | Havelock Vetinari removed Mustrum Ridcully from the crew of Ankh-Morpork 2010            |

  Scenario Outline: Ridcully resigns
    Given Ridcully is an existing crew member of the Ankh-Morpork 2010 project with role <role>
    When Ridcully resigns from the Ankh-Morpork 2010 project crew
    Then <user> is notified of the removal with <notification_string>

    Examples:
      | user     | role            | notification_string                                                   |
      | Ridcully | editor          | You resigned as editor of Ankh-Morpork 2010                           |
      | Vetinari | editor          | Mustrum Ridcully resigned as editor of Ankh-Morpork 2010              |
      | Vimes    | editor          | Mustrum Ridcully resigned as editor of Ankh-Morpork 2010              |
      | Ridcully | promoter        | You resigned as promoter of Ankh-Morpork 2010                         |
      | Vetinari | promoter        | Mustrum Ridcully resigned as promoter of Ankh-Morpork 2010            |
      | Vimes    | promoter        | Mustrum Ridcully resigned as promoter of Ankh-Morpork 2010            |
      | Ridcully | editor,promoter | You resigned as editor and promoter of Ankh-Morpork 2010              |
      | Vetinari | editor,promoter | Mustrum Ridcully resigned as editor and promoter of Ankh-Morpork 2010 |
      | Vimes    | editor,promoter | Mustrum Ridcully resigned as editor and promoter of Ankh-Morpork 2010 |
      | Ridcully | usher           | You resigned from the crew of Ankh-Morpork 2010                       |
      | Vetinari | usher           | Mustrum Ridcully resigned from the crew of Ankh-Morpork 2010          |
      | Vimes    | usher           | Mustrum Ridcully resigned from the crew of Ankh-Morpork 2010          |
