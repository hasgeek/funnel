Feature: Profile follow
    As a user,
    I want to be notified of the activites of an organization
    So I can participate in the creation of content or consume the final content.

    Scenario: Following a profile logged in
        Given A user is logged in
        And visits the organization's profile page

        When user clicks the follow button

        Then a modal opens up
        And a success message is diplayed
        And a social share option is displayed
        And when user closes pop-up the page will refresh
        And Follow button state changes to unfollow

    Scenario: Following a profile without logging in
        Given A user is visiting the organization's profile page

        When user click the follow button

        Then login screen appears
        And a success message is diplayed
        And a social share option is displayed
        And when user closes pop-up the page will refresh
        And Follow button state changes to unfollow
