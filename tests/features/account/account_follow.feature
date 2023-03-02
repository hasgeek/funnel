# BIGGER GOAL
Feature: Account Follow
  As a user,
  I want to follow the activities of an organization,
  So I can participate in the activities of the organization

  # SMALLER AND SPECIFIC (SUB-FEATURES)
  Scenario: Logged in user follows a public organization
    # THIS CAN ALSO BE INCLUDED IN A BACKGROUND STEP IF IT IS REPETITIVE
    Given the user is logged in
    And the organization is public
    When the user visits the organization page
    And clicks on the 'Follow' button
    Then the user sees a success message pop-up on the org page
    And the button state changes to 'Following'

  Scenario: Logged in user follows a private organization
    Given the user is logged in
    And the organization is private
    When the user visits the organization page
    And clicks on the 'Follow' button
    Then the user sees a success message 'Request pending' on the org page
    And the button state changes to 'Requested'

  Scenario: Logged out user follows a public organization
    Given the organization is public
    When the user visits the organization page
    And clicks on the 'Follow' button
    Then user sees the login screen and logs in
    And user sees a success message 'Following' on the org page
    And the button state changes to 'Following'

  Scenario: Logged out user follows a private organization
    Given the organization is private
    When the user visits the organization page
    And clicks on the 'Follow' button
    Then user sees the login screen and logs in
    And user sees a success message 'Request Pending' on the org page
    And the button state changes to 'Requested'
