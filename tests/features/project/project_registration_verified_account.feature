Feature: Project registration with user account

  Background:
    Given User is on the project page
    And User is willing to share contact information

  Scenario: User is logged-in
    Given User is logged-in to account
    When User clicks the register button
    Then User should see a pop-up modal asking for consent to share contact info with the project promoter
    And User consents to share contact info
    And User is redirected to the project page
    And the project registration count increments by 1

  Scenario: User has an account and is not logged-in
    Given User is not logged-in to account
    When User clicks the register button
    And User successfully login to account
    Then User should see a pop-up modal asking for consent to share contact info with the project promoter
    And User consents to share contact info
    And User is redirected to the project page
    And the project registration count increments by 1

  Scenario: User has an account and enters invalid phone number to log-in
    Given User is not logged-in to account
    When User clicks the register button
    And User enters an invalid phone number
    Then User should an error message below the input field

  Scenario: User has an account and enters invalid email address/password to log-in
    Given User is not logged-in to account
    When User clicks the register button
    And User enters an invalid email address/password pair
    Then User should see an error message below the password field

  Scenario: User has an account and has forgotten the log-in password
    Given User is not logged-in to account
    When User clicks the register button
    And User chooses to log-in using email
    And User clicks 'forgot password'
    Then User should be redirected to the 'Reset password' page

  Scenario: User does not have an account
    Given User does not have an account
    When User clicks the register button
    And User enters valid contact information
    And User enters my name in the 'Your name' input field
    And User successfully verifies with a valid OTP
    Then User should see a pop-up modal asking for consent to share contact info with the project promoter
    And User consents to share contact info
    And User is redirected to the project page
    And the project registration count increments by 1

  Scenario: User does not have an account and enters an invalid phone-number to create an account
    Given User does not have an account
    When User clicks the register button
    And User enters an invalid phone number
    Then User should an error message below the input field

  Scenario: User does not have an account and enters an invalid email address to create an account
    Given User does not have a user account
    When User clicks the register button
    And User enters an invalid email address
    Then OTP message delivery fails
