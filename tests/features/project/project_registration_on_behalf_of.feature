Feature: Register a friend

  Background:
    Given Vetinari is on the project page
    And Vetinari wants to register for the project on behalf of Vimes

  Scenario: Vetinari is logged-in and has not registered for the project
    Given Vetinari is logged-in to account
    And Vetinari has not registered for the project
    When Vetinari clicks the register button
    Then Vetinari can send a registration link to Vimes' contact detail

  Scenario: Vetinari is not logged-in and has not registered for the project
    Given Vetinari is not logged-in to account
    And Vetinari has not registered for the project
    When Vetinari clicks the register button
    Then Vetinari can send a registration link to Vimes' contact detail

  Scenario: Vetinari has registered for the project and Vimes has an account
    Given Vetinari is logged-in to account
    And Vetinari is registered for the project
    And Vimes has an account
    When Vetinari registers on behalf of Vimes
    Then Vimes recieves an notification stating the OTP that has to be shared with Vetinari in-order to complete the registration

  Scenario: Vetinari has registered for the project and Vimes does not have an account
    Given Vetinari is logged-in to account
    And Vetinari is registered for the project
    And Vimes does not have an account
    When Vetinari registers on behalf of Vimes
    Then Vimes recieves an notification stating the OTP that has to be shared with Vetinari in-order to complete the registration

  Scenario: Vetinari has a temporary account
    Given Vetinari is logged-in to temporary account
    When Vetinari tries to registers on behalf of Vimes
    Then Vetinari is prompted to complete account verification to register on behalf of friend
