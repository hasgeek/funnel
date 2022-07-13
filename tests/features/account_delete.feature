Feature: Account Delete
    As a user,
    I want to delete my account.

    Scenario: User visits the delete endpoint
        Given the user is logged in
        When the user hits the delete endpoint
        Then AccountDeleteForm is displayed
