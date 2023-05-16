Feature: Account Subscribe
  As a user,
  I want to subscribe to an organization,
  So I can participate in the activities of the organization

  Background:
    Given the user the logged out
    And has opened the subscription pricing modal
    And chooses one of the subscription options option

  Scenario: Logged out proceeds to checkout
    Given the user has read the details about the subscription tier
    And reviewed the order summary
    When the user clicks the checkout button
    Then the user is redirected to the login page
