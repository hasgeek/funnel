Feature: Account creation
  A visitor can create an account through many prompts

  Scenario Outline: Anonymous visitor tries to login with a phone number
    # Given the browser locale is <language>
    Given Anonymous visitor is on the home page
    When they navigate to the login page and submit a phone number
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

  # Examples:
  # | language |
  # | en       |
  # | hi       |
  Scenario: Anonymous visitor tries to login with an email address
    Given Anonymous visitor is on the home page
    When they navigate to the login page and submit an email address
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

  Scenario: Twoflower tries to login with an email address password
    Given Twoflower visitor is on the home page
    When they navigate to the login page
    And submit an email address with password
    Then they are logged in

  Scenario: Twoflower tries to login with a phone number password
    Given Twoflower visitor is on the home page
    When they navigate to the login page
    And submit a phone number with password
    Then they are logged in

  Scenario: Anonymous visitor tries to login with an email address from the project page
    Given Anonymous visitor is on a project page
    When they click on follow
    Then a register modal appears
    When they enter an email address
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

  Scenario: Anonymous visitor tries to login with a phone number from the project page
    Given Anonymous visitor is on a project page
    When they click on follow
    Then a register modal appears
    When they enter a phone number
    Then they are prompted for their name and the OTP, which they provide
    And they get an account and are logged in

  Scenario: Twoflower tries to login with an email address from the project page
    Given Twoflower is on the project page
    When they click on follow
    Then a register modal appears
    When they submit the email address with password
    Then they are logged in

  Scenario: Twoflower tries to login with a phone number from the project page
    Given Twoflower is on the project page
    When they click on follow
    Then a register modal appears
    When they submit the phone number with password
    Then they are logged in
