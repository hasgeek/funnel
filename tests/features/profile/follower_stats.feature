Feature: Follower count
    As a user,
    I want to know more about the followers in an org,
    So it helps me make a decision on whether I want to follow the org or not


    Scenario: User (Non-Follower) visits a Public Org page

        Given the user is not a follower
        And the organization is public

        When the user clicks on the follower count

        Then a list containing the public identity of individual followers is visible to them


    Scenario: User (Follower) visits a Public Org page

        Given the user is a follower
        And the organization is public

        When the user clicks on the follower count

        Then a list containing the public identity of individual followers is visible to them


    Scenario: User (Non-Follower) visits a Private Org page

        Given the user is not a follower
        And the organization is private

        When the user clicks a follower count

        Then a notification appears that 'this list is only available to the followers' of the org


    Scenario: User (Follower) visits a Private Org page

        Given the user is a follower
        And the organization is private

        When a user clicks a follower count

        Then a list containing the public identity of individual followers is visible to them
