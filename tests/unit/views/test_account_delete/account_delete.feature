Feature: Account Delete
    As a user,
    I want to delete my account and all the data.

    Scenario: User Rincewind visits the delete endpoint
        Given user Rincewind is logged in
        When user Rincewind visits the delete endpoint
        Then user Rincewind is prompter for delete confirmation

    Scenario: User Ridcully visits the delete endpoint
        Given user Ridcully is logged in
        And user Ridcully is the sole owner of Unseen University
        When user Ridcully visits the delete endpoint
        Then 'This account has organizations without co-owners' warning is shown to the user

    Scenario: User Librarian visits the delete endpoint
        Given user Librarian is logged in
        And user Librarian is a co-owner of Unseen University
        When user Librarian hits the delete endpoint
        Then user Librarian is prompted for delete confirmation

    Scenario: User Librarian having a protected profile visits the delete endpoint
        Given user Librarian has a protected profile
        And user Librarian is logged in
        When user Librarian visits the delete endpoint
        Then 'This account is protected' warning is shown to the user
