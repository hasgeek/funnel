Feature: Project registration using temporary account

  Background:
    Given The user is on the project page
    And wants to register for the project using a temporary account

  Scenario: User is logged-in to an existing temporary account
    Given User is logged-in to temporary account
    When User clicks the register button
    Then User sees a modal confirming their registration
    And User is redirected to project page when they close the modal
    And User sees a toast below the temporary account avatar prompting account verification
    And Registration count increments by 1 on the project page

  Scenario: User creates a temporary account
    Given User is not logged-in to account
    And User clicks the register button
    When User chooses to sign-in with a temporary account in the log-in modal
    And User enters a valid 'Username' in the modal
    And User clicks the confirm button
    Then User sees a modal confirming their registration
    And User is redirected to project page when they close the modal
    And User sees a toast below the temporary account avatar prompting account verification
    And Registration count increments by 1 on the project page

  Scenario: User tries to create a temporary account with an existing username
    Given User is not logged-in to account
    And User clicks the register button
    When User chooses to sign-in with a temporary account in the log-in modal
    And User enters an existing 'Username' in the modal
    And User clicks the confirm button
    Then User sees a error message under the input field indicating the username is already taken
    And User remains on the registration modal

  Scenario: User tries to create a temporary account with an invalid username
    Given User is not logged-in to account
    And User clicks the register button
    When User chooses to sign-in with a temporary account in the log-in modal
    And User enters an invalid 'Username' in the modal
    And User clicks the confirm button
    Then User sees a error message under the input field indicating the username is invalid
    And User remains on the registration modal

  Scenario: User tries to create a temporary account without a username
    Given User is not logged-in to account
    And User clicks the register button
    When User chooses to sign-in with a temporary account in the log-in modal
    And User clicks the confirm button without entering a 'Username'
    Then User sees a error message under the input field indicating a username is needed
    And User remains on the registration modal
