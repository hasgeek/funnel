Feature: Account Login
  As a user,
  I want to login to my account in multiple ways

  Scenario: Twoflower signs up from the login page using phone
    Given Twoflower visits the login page
    And they enter the phone number
    When they click on get otp
    And enter their name with correct otp
    Then they get "You are now logged in" flash message

  Scenario: Twoflower signs up from the login page using email
    Given Twoflower visits the login page
    And they enter the email
    When they click on get otp
    And enter their name with correct otp
    Then they get "You are now logged in" flash message
