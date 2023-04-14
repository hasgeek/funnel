# Project actions have poor communication about consequences of changing project status
Feature: Project status for crew members
  As a crew member,
  I would like to be informed of the current status of the project
  So I can determine the next steps.

  Scenario Outline: Crew-member is informed about the project state.
    Given the user is a crew member
    When the project is in the <x> state
    Then the crew member can see a label for the current <x> state

    Examples:
      | x         |
      | draft     |
      | published |
      | withdrawn |
