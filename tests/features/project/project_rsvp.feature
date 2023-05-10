Feature: Custom RSVP form

  Background:
    Given Vetinari is the editor of Project Expo 2010
    And Project Expo 2010 is published

  Scenario: Vetinari is logged-in and wants to create a custom RSVP form
    Given Vetinari is logged-in and visits the tickets page
    When Vetinari adds the right fields using a valid JSON and sumbits
    Then the user can register to the project by filling the form
    And Vetinari can see the details of the participants from the participants tab

  Scenario: Twoflower is logged-in and wants to register to the project
    Given Twoflower is logged-in and visits the project registration page
    And the Project Expo 2010 is published
    When Twoflower fills the form and submits
    Then Twoflower is registered to the project
