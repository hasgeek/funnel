Feature: Project Crew Notification
  As a project crew member, I want to be notified of changes to the crew, with a message
  telling me exactly what has changed and who did it

  Background:
    Given Vetinari is an owner of the Ankh-Morpork organization
    And Vetinari is an editor and promoter of the Ankh-Morpork 2010 project
    And Vimes is a promoter of the Ankh-Morpork 2010 project

  Scenario Outline: Ridcully is added to a project
    When Vetinari adds Ridcully with role <role> to the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the addition

    Examples:
      | recipient | role            | actor    | notification_string                                                                     |
      | Vetinari  | editor          | Ridcully | You made Mustrum Ridcully an editor of Ankh-Morpork 2010                                |
      | Ridcully  | editor          | Vetinari | Havelock Vetinari made you an editor of Ankh-Morpork 2010                               |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully was made editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Vetinari  | promoter        | Ridcully | You made Mustrum Ridcully a promoter of Ankh-Morpork 2010                               |
      | Ridcully  | promoter        | Vetinari | Havelock Vetinari made you a promoter of Ankh-Morpork 2010                              |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully was made promoter of Ankh-Morpork 2010 by Havelock Vetinari            |
      | Vetinari  | editor,promoter | Ridcully | You made Mustrum Ridcully an editor and promoter of Ankh-Morpork 2010                   |
      | Ridcully  | editor,promoter | Vetinari | Havelock Vetinari made you an editor and promoter of Ankh-Morpork 2010                  |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully was made editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Vetinari  | usher           | Ridcully | You added Mustrum Ridcully to the crew of Ankh-Morpork 2010                             |
      | Ridcully  | usher           | Vetinari | Havelock Vetinari added you to the crew of Ankh-Morpork 2010                            |
      | Vimes     | usher           | Ridcully | Havelock Vetinari added Mustrum Ridcully to the crew of Ankh-Morpork 2010               |

  Scenario Outline: Ridcully adds themself
    Given Vetinari made Ridcully an admin of Ankh-Morpork
    When Ridcully adds themself with role <role> to the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the addition

    Examples:
      | recipient | role            | actor    | notification_string                                              |
      | Ridcully  | editor          | Ridcully | You joined Ankh-Morpork 2010 as editor                           |
      | Vetinari  | editor          | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as editor              |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as editor              |
      | Ridcully  | promoter        | Ridcully | You joined Ankh-Morpork 2010 as promoter                         |
      | Vetinari  | promoter        | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as promoter            |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as promoter            |
      | Ridcully  | editor,promoter | Ridcully | You joined Ankh-Morpork 2010 as editor and promoter              |
      | Vetinari  | editor,promoter | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as editor and promoter |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully joined Ankh-Morpork 2010 as editor and promoter |
      | Ridcully  | usher           | Ridcully | You joined the crew of Ankh-Morpork 2010                         |
      | Vetinari  | usher           | Ridcully | Mustrum Ridcully joined the crew of Ankh-Morpork 2010            |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully joined the crew of Ankh-Morpork 2010            |

  Scenario Outline: Vetinari invites Ridcully
    When Vetinari invites Ridcully with role <role> to the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the invitation

    Examples:
      | recipient | role            | actor    | notification_string                                                                                 |
      | Vetinari  | editor          | Ridcully | You invited Mustrum Ridcully to be an editor of Ankh-Morpork 2010                                   |
      | Ridcully  | editor          | Vetinari | Havelock Vetinari invited you to be an editor of Ankh-Morpork 2010                                  |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully was invited to be an editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Vetinari  | promoter        | Ridcully | You invited Mustrum Ridcully to be a promoter of Ankh-Morpork 2010                                  |
      | Ridcully  | promoter        | Vetinari | Havelock Vetinari invited you to be a promoter of Ankh-Morpork 2010                                 |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully was invited to be a promoter of Ankh-Morpork 2010 by Havelock Vetinari             |
      | Vetinari  | editor,promoter | Ridcully | You invited Mustrum Ridcully to be an editor and promoter of Ankh-Morpork 2010                      |
      | Ridcully  | editor,promoter | Vetinari | Havelock Vetinari invited you to be an editor and promoter of Ankh-Morpork 2010                     |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully was invited to be an editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Vetinari  | usher           | Ridcully | You invited Mustrum Ridcully to join the crew of Ankh-Morpork 2010                                  |
      | Ridcully  | usher           | Vetinari | Havelock Vetinari invited you to join the crew of Ankh-Morpork 2010                                 |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully was invited to join the crew of Ankh-Morpork 2010 by Havelock Vetinari             |

  Scenario Outline: Ridcully accepted the invite
    Given Vetinari invited Ridcully with role <role> to the Ankh-Morpork 2010 project
    When Ridcully accepts the invitation to be a crew member of the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the acceptance

    Examples:
      | recipient | role            | actor    | notification_string                                                                |
      | Ridcully  | editor          | Ridcully | You accepted an invite to be editor of Ankh-Morpork 2010                           |
      | Vetinari  | editor          | Ridcully | Mustrum Ridcully accepted an invite to be editor of Ankh-Morpork 2010              |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully accepted an invite to be editor of Ankh-Morpork 2010              |
      | Ridcully  | promoter        | Ridcully | You accepted an invite to be promoter of Ankh-Morpork 2010                         |
      | Vetinari  | promoter        | Ridcully | Mustrum Ridcully accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully accepted an invite to be promoter of Ankh-Morpork 2010            |
      | Ridcully  | editor,promoter | Ridcully | You accepted an invite to be editor and promoter of Ankh-Morpork 2010              |
      | Vetinari  | editor,promoter | Ridcully | Mustrum Ridcully accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully accepted an invite to be editor and promoter of Ankh-Morpork 2010 |
      | Ridcully  | usher           | Ridcully | You accepted an invite to join the crew of Ankh-Morpork 2010                       |
      | Vetinari  | usher           | Ridcully | Mustrum Ridcully accepted an invite to join the crew of Ankh-Morpork 2010          |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully accepted an invite to join the crew of Ankh-Morpork 2010          |

  Scenario Outline: Vetinari changes Ridcully's role
    Given Ridcully is an existing crew member with roles editor, promoter and usher of the Ankh-Morpork 2010 project
    When Vetinari changes Ridcully's role to <role> in the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the change

    Examples:
      | recipient | role            | actor    | notification_string                                                                                  |
      | Vetinari  | editor          | Ridcully | You changed Mustrum Ridcully's role to editor of Ankh-Morpork 2010                                   |
      | Ridcully  | editor          | Vetinari | Havelock Vetinari changed your role to editor of Ankh-Morpork 2010                                   |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully's role to editor of Ankh-Morpork 2010 was changed by Havelock Vetinari              |
      | Vetinari  | promoter        | Ridcully | You changed Mustrum Ridcully's role to promoter of Ankh-Morpork 2010                                 |
      | Ridcully  | promoter        | Vetinari | Havelock Vetinari changed your role to promoter of Ankh-Morpork 2010                                 |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully's role to promoter of Ankh-Morpork 2010 was changed by Havelock Vetinari            |
      | Vetinari  | editor,promoter | Ridcully | You changed Mustrum Ridcully's role to editor and promoter of Ankh-Morpork 2010                      |
      | Ridcully  | editor,promoter | Vetinari | Havelock Vetinari changed your role to editor and promoter of Ankh-Morpork 2010                      |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully's role to editor and promoter of Ankh-Morpork 2010 was changed by Havelock Vetinari |
      | Vetinari  | usher           | Ridcully | You changed Mustrum Ridcully's role to crew member of Ankh-Morpork 2010                              |
      | Ridcully  | usher           | Vetinari | Havelock Vetinari changed your role to crew member of Ankh-Morpork 2010                              |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully's role to crew member of Ankh-Morpork 2010 was changed by Havelock Vetinari         |

  Scenario Outline: Ridcully changed their own role
    Given Vetinari made Ridcully an admin of Ankh-Morpork
    And Ridcully is an existing crew member with roles editor, promoter and usher of the Ankh-Morpork 2010 project
    When Ridcully changes their role to <role> in the Ankh-Morpork 2010 project
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the change

    Examples:
      | recipient | role            | actor    | notification_string                                                             |
      | Ridcully  | editor          | Ridcully | You changed your role to editor of Ankh-Morpork 2010                            |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully changed their role to editor of Ankh-Morpork 2010              |
      | Vetinari  | editor          | Ridcully | Mustrum Ridcully changed their role to editor of Ankh-Morpork 2010              |
      | Ridcully  | promoter        | Ridcully | You changed your role to promoter of Ankh-Morpork 2010                          |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully changed their role to promoter of Ankh-Morpork 2010            |
      | Vetinari  | promoter        | Ridcully | Mustrum Ridcully changed their role to promoter of Ankh-Morpork 2010            |
      | Ridcully  | editor,promoter | Ridcully | You are now editor and promoter of Ankh-Morpork 2010                            |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully changed their role to editor and promoter of Ankh-Morpork 2010 |
      | Vetinari  | editor,promoter | Ridcully | Mustrum Ridcully changed their role to editor and promoter of Ankh-Morpork 2010 |
      | Ridcully  | usher           | Ridcully | You changed your role to crew member of Ankh-Morpork 2010                       |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully changed their role to crew member of Ankh-Morpork 2010         |
      | Vetinari  | usher           | Ridcully | Mustrum Ridcully changed their role to crew member of Ankh-Morpork 2010         |

  Scenario Outline: Vetinari removes Ridcully
    Given Ridcully is an existing crew member of the Ankh-Morpork 2010 project with role <role>
    When Vetinari removes Ridcully from the Ankh-Morpork 2010 project crew
    Then <recipient> is notified of the removal with photo of <actor> and message <notification_string>

    Examples:
      | recipient | role            | actor    | notification_string                                                                           |
      | Vetinari  | editor          | Ridcully | You removed Mustrum Ridcully from editor of Ankh-Morpork 2010                                 |
      | Ridcully  | editor          | Vetinari | Havelock Vetinari removed you from editor of Ankh-Morpork 2010                                |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully was removed as editor of Ankh-Morpork 2010 by Havelock Vetinari              |
      | Vetinari  | promoter        | Ridcully | You removed Mustrum Ridcully from promoter of Ankh-Morpork 2010                               |
      | Ridcully  | promoter        | Vetinari | Havelock Vetinari removed you from promoter of Ankh-Morpork 2010                              |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully was removed as promoter of Ankh-Morpork 2010 by Havelock Vetinari            |
      | Vetinari  | editor,promoter | Ridcully | You removed Mustrum Ridcully from editor and promoter of Ankh-Morpork 2010                    |
      | Ridcully  | editor,promoter | Vetinari | Havelock Vetinari removed you from editor and promoter of Ankh-Morpork 2010                   |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully was removed as editor and promoter of Ankh-Morpork 2010 by Havelock Vetinari |
      | Vetinari  | usher           | Ridcully | You removed Mustrum Ridcully from the crew of Ankh-Morpork 2010                               |
      | Ridcully  | usher           | Vetinari | Havelock Vetinari removed you from the crew of Ankh-Morpork 2010                              |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully was removed as crew of Ankh-Morpork 2010 by Havelock Vetinari                |

  Scenario Outline: Ridcully resigns
    Given Ridcully is an existing crew member of the Ankh-Morpork 2010 project with role <role>
    When Ridcully resigns from the Ankh-Morpork 2010 project crew
    Then <recipient> is notified of the removal with photo of <actor> and message <notification_string>

    Examples:
      | recipient | role            | actor    | notification_string                                                   |
      | Ridcully  | editor          | Ridcully | You resigned as editor of Ankh-Morpork 2010                           |
      | Vetinari  | editor          | Ridcully | Mustrum Ridcully resigned as editor of Ankh-Morpork 2010              |
      | Vimes     | editor          | Ridcully | Mustrum Ridcully resigned as editor of Ankh-Morpork 2010              |
      | Ridcully  | promoter        | Ridcully | You resigned as promoter of Ankh-Morpork 2010                         |
      | Vetinari  | promoter        | Ridcully | Mustrum Ridcully resigned as promoter of Ankh-Morpork 2010            |
      | Vimes     | promoter        | Ridcully | Mustrum Ridcully resigned as promoter of Ankh-Morpork 2010            |
      | Ridcully  | editor,promoter | Ridcully | You resigned as editor and promoter of Ankh-Morpork 2010              |
      | Vetinari  | editor,promoter | Ridcully | Mustrum Ridcully resigned as editor and promoter of Ankh-Morpork 2010 |
      | Vimes     | editor,promoter | Ridcully | Mustrum Ridcully resigned as editor and promoter of Ankh-Morpork 2010 |
      | Ridcully  | usher           | Ridcully | You resigned from the crew of Ankh-Morpork 2010                       |
      | Vetinari  | usher           | Ridcully | Mustrum Ridcully resigned from the crew of Ankh-Morpork 2010          |
      | Vimes     | usher           | Ridcully | Mustrum Ridcully resigned from the crew of Ankh-Morpork 2010          |
