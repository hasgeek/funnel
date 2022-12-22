Feature: Organization Admin Notification
  As an Organization admin, I want to be notified when another admin
  is added, removed or has their role changed.

  Background:
    Given Vetinari is an owner of the Ankh-Morpork organization
    And Vimes is an admin of the Ankh-Morpork organization

  Scenario Outline: Vetinari adds Ridcully
    When Vetinari adds Ridcully as <owner_or_admin>
    Then <user> gets notified with <notification_string> about the addition

    Examples:
      | user     | owner_or_admin | notification_string                                           |
      | Vetinari | owner          | You made Mustrum Ridcully owner of Ankh-Morpork               |
      | Ridcully | owner          | Havelock Vetinari made you owner of Ankh-Morpork              |
      | Vimes    | owner          | Havelock Vetinari made Mustrum Ridcully owner of Ankh-Morpork |
      | Vetinari | admin          | You made Mustrum Ridcully admin of Ankh-Morpork               |
      | Ridcully | admin          | Havelock Vetinari made you admin of Ankh-Morpork              |
      | Vimes    | admin          | Havelock Vetinari made Mustrum Ridcully admin of Ankh-Morpork |

  Scenario Outline: Vetinari invites Ridcully
    When Vetinari invites Ridcully as <owner_or_admin>
    Then <user> gets notified with <notification_string> about the invitation

    Examples:
      | user     | owner_or_admin | notification_string                                                    |
      | Vetinari | owner          | You invited Mustrum Ridcully to be owner of Ankh-Morpork               |
      | Ridcully | owner          | Havelock Vetinari invited you to be owner of Ankh-Morpork              |
      | Vimes    | owner          | Havelock Vetinari invited Mustrum Ridcully to be owner of Ankh-Morpork |
      | Vetinari | admin          | You invited Mustrum Ridcully to be admin of Ankh-Morpork               |
      | Ridcully | admin          | Havelock Vetinari invited you to be admin of Ankh-Morpork              |
      | Vimes    | admin          | Havelock Vetinari invited Mustrum Ridcully to be admin of Ankh-Morpork |

  Scenario Outline: Ridcully accepts the invite
    Given Vetinari invites Ridcully as <owner_or_admin>
    When Ridcully accepts the invitation to be admin
    Then <user> gets notified with <notification_string> about the acceptance

    Examples:
      | user     | owner_or_admin | notification_string                                             |
      | Ridcully | owner          | You accepted an invite to be owner of Ankh-Morpork              |
      | Vetinari | owner          | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Vimes    | owner          | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Ridcully | admin          | You accepted an invite to be admin of Ankh-Morpork              |
      | Vetinari | admin          | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |
      | Vimes    | admin          | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |

  Scenario Outline: Vetinari changes Ridcully's role
    Given Ridcully is currently <owner_or_admin>
    When Vetinari changes Ridcully to <new_role>
    Then <user> gets notified with <notification_string> about the change

    Examples:
      | user     | owner_or_admin | new_role | notification_string                                                        |
      | Vetinari | owner          | admin    | You changed Mustrum Ridcully's role to admin of Ankh-Morpork               |
      | Ridcully | owner          | admin    | Havelock Vetinari changed your role to admin of Ankh-Morpork               |
      | Vimes    | owner          | admin    | Havelock Vetinari changed Mustrum Ridcully's role to admin of Ankh-Morpork |
      | Vetinari | admin          | owner    | You changed Mustrum Ridcully's role to owner of Ankh-Morpork               |
      | Ridcully | admin          | owner    | Havelock Vetinari changed your role to owner of Ankh-Morpork               |
      | Vimes    | admin          | owner    | Havelock Vetinari changed Mustrum Ridcully's role to owner of Ankh-Morpork |

  Scenario Outline: Vetinari removes Ridcully
    Given Ridcully is currently <owner_or_admin>
    When Vetinari removes Ridcully
    Then <user> gets notified with <notification_string> about the removal

    Examples:
      | user     | owner_or_admin | notification_string                                                   |
      | Vetinari | owner          | You removed Mustrum Ridcully from owner of Ankh-Morpork               |
      | Ridcully | owner          | Havelock Vetinari removed you from owner of Ankh-Morpork              |
      | Vimes    | owner          | Havelock Vetinari removed Mustrum Ridcully from owner of Ankh-Morpork |
      | Vetinari | admin          | You removed Mustrum Ridcully from admin of Ankh-Morpork               |
      | Ridcully | admin          | Havelock Vetinari removed you from admin of Ankh-Morpork              |
      | Vimes    | admin          | Havelock Vetinari removed Mustrum Ridcully from admin of Ankh-Morpork |
