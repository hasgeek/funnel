Feature: Organization Admin Notification
  As an Organization admin, I want to be notified of changes to the other admins, with a message
  telling me exactly what has changed and who did it

  Background:
    Given Vetinari is an owner of the Ankh-Morpork organization
    And Vimes is an admin of the Ankh-Morpork organization

  Scenario Outline: Vetinari adds Ridcully
    When Vetinari adds Ridcully with the role <role>
    Then <user> gets notified with <notification_string> about the addition

    Examples:
      | user     | role  | notification_string                                           |
      | Vetinari | owner | You made Mustrum Ridcully owner of Ankh-Morpork               |
      | Ridcully | owner | Havelock Vetinari made you owner of Ankh-Morpork              |
      | Vimes    | owner | Havelock Vetinari made Mustrum Ridcully owner of Ankh-Morpork |
      | Vetinari | admin | You made Mustrum Ridcully admin of Ankh-Morpork               |
      | Ridcully | admin | Havelock Vetinari made you admin of Ankh-Morpork              |
      | Vimes    | admin | Havelock Vetinari made Mustrum Ridcully admin of Ankh-Morpork |

  Scenario Outline: Vetinari invites Ridcully
    When Vetinari invites Ridcully with the role <role> to the Ankh-Morpork organization
    Then <user> gets notified with <notification_string> about the invitation

    Examples:
      | user     | role  | notification_string                                                    |
      | Vetinari | owner | You invited Mustrum Ridcully to be owner of Ankh-Morpork               |
      | Ridcully | owner | Havelock Vetinari invited you to be owner of Ankh-Morpork              |
      | Vimes    | owner | Havelock Vetinari invited Mustrum Ridcully to be owner of Ankh-Morpork |
      | Vetinari | admin | You invited Mustrum Ridcully to be admin of Ankh-Morpork               |
      | Ridcully | admin | Havelock Vetinari invited you to be admin of Ankh-Morpork              |
      | Vimes    | admin | Havelock Vetinari invited Mustrum Ridcully to be admin of Ankh-Morpork |

  Scenario Outline: Ridcully accepted the invite
    Given Vetinari invites Ridcully with role <role> to the Ankh-Morpork organization
    When Ridcully accepts the invitation to be an admin member of the Ankh-Morpork organization
    Then <user> gets notified with <notification_string> about the acceptance

    Examples:
      | user     | role  | notification_string                                             |
      | Ridcully | owner | You accepted an invite to be owner of Ankh-Morpork              |
      | Vetinari | owner | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Vimes    | owner | Mustrum Ridcully accepted an invite to be owner of Ankh-Morpork |
      | Ridcully | admin | You accepted an invite to be admin of Ankh-Morpork              |
      | Vetinari | admin | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |
      | Vimes    | admin | Mustrum Ridcully accepted an invite to be admin of Ankh-Morpork |

  Scenario Outline: Vetinari changes Ridcully's role
    Given Ridcully is an existing admin with roles <from_role> of the Ankh-Morpork organization
    When Vetinari changes Ridcully's role to <to_role> in the Ankh-Morpork organization
    Then <user> gets notified with <notification_string> about the change

    Examples:
      | user     | from_role | to_role | notification_string                                                        |
      | Vetinari | owner     | admin   | You changed Mustrum Ridcully's role to admin of Ankh-Morpork               |
      | Ridcully | owner     | admin   | Havelock Vetinari changed your role to admin of Ankh-Morpork               |
      | Vimes    | owner     | admin   | Havelock Vetinari changed Mustrum Ridcully's role to admin of Ankh-Morpork |
      | Vetinari | admin     | owner   | You changed Mustrum Ridcully's role to owner of Ankh-Morpork               |
      | Ridcully | admin     | owner   | Havelock Vetinari changed your role to owner of Ankh-Morpork               |
      | Vimes    | admin     | owner   | Havelock Vetinari changed Mustrum Ridcully's role to owner of Ankh-Morpork |

  Scenario Outline: Vetinari removes Ridcully
    Given Ridcully is an existing admin with roles <role> of the Ankh-Morpork organization
    When Vetinari removes Ridcully from the Ankh-Morpork organization
    Then <user> gets notified with <notification_string> about the removal

    Examples:
      | user     | role  | notification_string                                                   |
      | Vetinari | owner | You removed Mustrum Ridcully from owner of Ankh-Morpork               |
      | Ridcully | owner | Havelock Vetinari removed you from owner of Ankh-Morpork              |
      | Vimes    | owner | Havelock Vetinari removed Mustrum Ridcully from owner of Ankh-Morpork |
      | Vetinari | admin | You removed Mustrum Ridcully from admin of Ankh-Morpork               |
      | Ridcully | admin | Havelock Vetinari removed you from admin of Ankh-Morpork              |
      | Vimes    | admin | Havelock Vetinari removed Mustrum Ridcully from admin of Ankh-Morpork |
