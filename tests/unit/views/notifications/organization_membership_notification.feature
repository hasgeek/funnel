Feature: Organization Admin Notification
  As an Organization admin, I want to be notified when another admin
  is added, removed or has their role changed.

  Background:
    Given Vetinari is an owner of the Ankh-Morpork organization
    And Vimes is an admin of the Ankh-Morpork organization

  Scenario Outline: Vetinari adds Ridcully
    When Vetinari adds Ridcully as <role>
    Then <recipient> gets notified with a photo of <actor> and message <notification_string> about the addition

    Examples:
      | recipient | role  | actor    | notification_string                                                  |
      | Vetinari  | owner | Ridcully | You made Mustrum Ridcully owner of Ankh-Morpork                      |
      | Ridcully  | owner | Vetinari | Havelock Vetinari made you owner of Ankh-Morpork                     |
      | Vimes     | owner | Ridcully | Mustrum Ridcully was made owner of Ankh-Morpork by Havelock Vetinari |
      | Vetinari  | admin | Ridcully | You made Mustrum Ridcully admin of Ankh-Morpork                      |
      | Ridcully  | admin | Vetinari | Havelock Vetinari made you admin of Ankh-Morpork                     |
      | Vimes     | admin | Ridcully | Mustrum Ridcully was made admin of Ankh-Morpork by Havelock Vetinari |

  Scenario Outline: Vetinari invites Ridcully
    When Vetinari invites Ridcully as <role>
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the invitation

    Examples:
      | recipient | role  | actor    | notification_string                                                           |
      | Vetinari  | owner | Ridcully | You invited Mustrum Ridcully to be owner of Ankh-Morpork                      |
      | Ridcully  | owner | Vetinari | Havelock Vetinari invited you to be owner of Ankh-Morpork                     |
      | Vimes     | owner | Ridcully | Mustrum Ridcully was invited to be owner of Ankh-Morpork by Havelock Vetinari |
      | Vetinari  | admin | Ridcully | You invited Mustrum Ridcully to be admin of Ankh-Morpork                      |
      | Ridcully  | admin | Vetinari | Havelock Vetinari invited you to be admin of Ankh-Morpork                     |
      | Vimes     | admin | Ridcully | Mustrum Ridcully was invited to be admin of Ankh-Morpork by Havelock Vetinari |

  Scenario Outline: Ridcully accepts the invite
    Given Vetinari invites Ridcully as <role>
    When Ridcully accepts the invitation to be admin
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the acceptance

    Examples:
      | recipient | role  | actor    | notification_string                                             |
      | Ridcully  | owner | Ridcully | You accepted an invite to be owner of Ankh-Morpork              |
      | Vetinari  | owner | Ridcully | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Vimes     | owner | Ridcully | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Ridcully  | admin | Ridcully | You accepted an invite to be admin of Ankh-Morpork              |
      | Vetinari  | admin | Ridcully | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |
      | Vimes     | admin | Ridcully | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |

  Scenario Outline: Vetinari changes Ridcully`s role
    Given Ridcully is currently <role>
    When Vetinari changes Ridcully to <new_role>
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the change

    Examples:
      | recipient | role  | new_role | actor    | notification_string                                                               |
      | Vetinari  | owner | admin    | Ridcully | You changed Mustrum Ridcully`s role to admin of Ankh-Morpork                      |
      | Ridcully  | owner | admin    | Vetinari | Havelock Vetinari changed your role to admin of Ankh-Morpork                      |
      | Vimes     | owner | admin    | Ridcully | Mustrum Ridcully`s role was changed to admin of Ankh-Morpork by Havelock Vetinari |
      | Vetinari  | admin | owner    | Ridcully | You changed Mustrum Ridcully`s role to owner of Ankh-Morpork                      |
      | Ridcully  | admin | owner    | Vetinari | Havelock Vetinari changed your role to owner of Ankh-Morpork                      |
      | Vimes     | admin | owner    | Ridcully | Mustrum Ridcully`s role was changed to owner of Ankh-Morpork by Havelock Vetinari |

  Scenario Outline: Vetinari removes Ridcully
    Given Ridcully is currently <role>
    When Vetinari removes Ridcully
    Then <recipient> gets notified with photo of <actor> and message <notification_string> about the removal

    Examples:
      | recipient | role  | actor    | notification_string                                                        |
      | Vetinari  | owner | Ridcully | You removed Mustrum Ridcully from owner of Ankh-Morpork                    |
      | Ridcully  | owner | Vetinari | Havelock Vetinari removed you from owner of Ankh-Morpork                   |
      | Vimes     | owner | Ridcully | Mustrum Ridcully was removed as owner of Ankh-Morpork by Havelock Vetinari |
      | Vetinari  | admin | Ridcully | You removed Mustrum Ridcully from admin of Ankh-Morpork                    |
      | Ridcully  | admin | Vetinari | Havelock Vetinari removed you from admin of Ankh-Morpork                   |
      | Vimes     | admin | Ridcully | Mustrum Ridcully was removed as admin of Ankh-Morpork by Havelock Vetinari |
