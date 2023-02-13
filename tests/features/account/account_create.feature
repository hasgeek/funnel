Feature: Account creation
  A visitor can create an account through many prompts

  Scenario: Anonymous visitor tries to login with a phone number
    Given Anonymous visitor is on the home page
    When they navigate to the login page and submit a phone number
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

  Scenario: Anonymous visitor tries to login with an email address
    Given Anonymous visitor is on the home page
    When they navigate to the login page and submit an email address
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

# TODO: create starting from project register popup
# TODO: create using external login
