Feature: Profile unfollow
    As a user,
    I want to unfollow from an organization,
    So I stop receiving notifications of the orgs activities across all communication channels


    Scenario: Logged in user unfollows a public organization

        Given the user is logged in
        And the organization is public

        When the user visits the organization page that they are following
        And clicks the 'Unfollow' button in the dropdown

        Then the user sees a success message 'Unfollowed' on the org page
        And the primary button state on the page changes to 'Follow'


    Scenario: Logged in user unfollows a private profile

        Given the user is logged in
        And the organization is private

        When the user visits the organization page that they are following
        And clicks the 'Unfollow' button in the dropdown

        Then the user sees a success message 'Unfollowed' on the org page
        And the primary button state on the page changes to 'Follow'
        And the user can no longer see the projects in the org
