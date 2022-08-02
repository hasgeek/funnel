Feature: Follower receives notifications
    As a follower,
    I want to receive notifications of the orgs activities,
    So I don't miss out on any of the activities

    Background:

        Given the user is logged in

    Scenario: Follower receives first notification after following

        Given the user clicks the follow button

        When the user successfully follows an organization

        Then the user receives a welcome message via sms and email


    Scenario: Follower receives a notification when org publishes a project

        Given the user is following an organization

        When the organization publishes a new project

        Then the user receives a 'New Project' notification


    Scenario: Follower receives a notification an hour before project goes live

        Given the user is following an organization

        When an organization's livestream is due in 1 hour

        Then the user receives a 'Livestream Coming Up' notification


    Scenario: Follower receives a notification 10 mins before project goes live

        Given the User is following an organization

        When an organization's livestream is due in 10 mins

        Then the user receives a 'Livestream in 10 mins' notification


    Scenario: Follower receives a notification of archived content

        Given the user is following an organization

        When an organization uploads videos to a project

        Then the user receives a 'link to video tabs' notification


    Scenario: Follower receives notifications of new submissions in a project

        Given the user is following an organization

        When an organization receives new submissions

        Then the user receives a truncated portion of the submission, with link to read the whole submission via SMS and Email


    Scenario: Follower gets notified of updates posted in project

        Given the user is following an organization

        When an organization posts a new update

        Then the user receives a truncated portion of the post, with link to read the whole update via SMS and Email

    Scenario: Follower receives one last notification after unfollowing the org

        Given the user navigates to the org page

        When the user clicks the 'Unfollow' button

        Then the user receives one last notification 'sorry to see you go' via email and SMS
