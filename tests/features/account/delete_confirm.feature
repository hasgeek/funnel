Feature: Account deletion safety check
  As a user, I want to delete my account and the site confirms it is safe to proceed
  because there is no blocking issue

  Scenario: Rincewind tries to delete their account
    Given Rincewind is logged in
    When they visit the delete page
    Then they are cleared to delete the account

  Scenario: Ridcully tries to delete their account
    Given Ridcully is logged in
    And they are the sole owner of Unseen University
    When they visit the delete page
    Then they are told they have organizations without co-owners

  Scenario: The Librarian tries to delete their account
    Given The Librarian is logged in
    And they are a co-owner of Unseen University
    When they visit the delete page
    Then they are cleared to delete the account

  Scenario: Death tries to delete their account
    Given Death has a protected account
    And they are logged in
    When they visit the delete page
    Then they are told their account is protected
