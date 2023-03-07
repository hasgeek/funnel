# Projects have poor discoverability from user's point of view
Feature: Project Status
  As a user,
  I would like to see the project status upfront across all project tabs
  So that I would be informed if the project that I am looking at is not the finished product.

  Scenario: User is informed when a project is in draft state.
    Given a project is in the draft state
    When the user visits the project page
    Then the user can see a label for the current project status
    And can access further information about what draft means in this context.

  Scenario: User is informed when a project is withdrawn.
    Given a project is in the withdrawn state
    When the user visits the project page
    Then the user can see a label for the current project status - draft
    And can access further information about what draft means in this context.
