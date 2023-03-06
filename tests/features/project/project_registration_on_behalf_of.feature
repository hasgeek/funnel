Feature: Register a friend

  Background:
    Given Vettinary is on the project page
    And Vettinary wants to register for the project on behalf of Vimes

  Scenario: Vettinary is logged-in and has not registered for the project
    Given Vettinary is logged-in to account
    And Vettinary has not registered for the project
    When Vettinary clicks the register button
    Then Vettinary can send a registration link to Vimes' contact detail

  Scenario: Vettinary is not logged-in and has not registered for the project
    Given Vettinary is not logged-in to account
    And Vettinary has not registered for the project
    When Vettinary clicks the register button
    Then Vettinary can send a registration link to Vimes' contact detail

  Scenario: Vettinary has registered for the project and Vimes has an account
    Given Vettinary is logged-in to account
    And Vettinary is registered for the project
    And Vimes has an account
    When Vettinary registers on behalf of Vimes
    Then Vimes recieves an notification stating the OTP that has to be shared with Vettinary in-order to complete the registration

  Scenario: Vettinary has registered for the project and Vimes does not have an account
    Given Vettinary is logged-in to account
    And Vettinary is registered for the project
    And Vimes does not have an account
    When Vettinary registers on behalf of Vimes
    Then Vimes recieves an notification stating the OTP that has to be shared with Vettinary in-order to complete the registration

  Scenario: Vettinary has a temporary account
    Given Vettinary is logged-in to temporary account
    When Vettinary tries to registers on behalf of Vimes
    Then Vettinary is prompted to complete account verification to register on behalf of friend
