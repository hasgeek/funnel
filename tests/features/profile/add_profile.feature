Feature: Profile creation

  Scenario Outline: Twoflower creates a profile
    Given Twoflower is logged in
    When they open account settings
    And create a new organization
    Then a profile will be created
