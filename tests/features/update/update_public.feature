Feature: Post a public update
  Havelock Vetinari is the editor of Ankh Morpork's annual expo.
  Vetinari wants to announce the 2011 edition, making the announcement publicly
  available and sending a copy to everyone who attended previous editions.

  Scenario: Vetinari posts a public notice
    Given the 2011 expo project has been published
    And Vetinari has drafted an update in this project for the public announcement
    When Vetinari publishes the update
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: Vetinari posts a public notice
    Given the 2011 expo project has been published
    And Vimes is also an editor of the 2011 expo project
    And Vimes has drafted an update in this project for the public announcement
    And Vimes has not published the update, leaving it to Vetinari to review
    When Vetinari publishes the update
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: the venue for 2011 expo project is announced.
    And Vimes wants to post an update about the venue and directions to reach the venue
    Given that Vimes has posted an update in this project for the venue announcement
    And Vimes has published the update
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: the 2011 expo project is one month away and Vimes wants to draft and schedule an update about the parking facilities and check-in system at the venue.
    Given that Vimes has drafted an update in this project about the parking facilities and check-in system at the venue
    And Vimes has scheduled the update for sending one month later
    Then the update is sent to everyone who signed up for the 2011 edition one month later
    And the update is sent to everyone who signed up for a past edition one month later

  Scenario: the first batch of speakers for 2011 expo project is ready for announcement three weeks before the 2011 expo and Vimes wants to post an update about announcing the names of the speakers and the topics of their talks
    Given that Vimes has drafted an update in this project for the public announcement
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: the draft schedule for expo 2011 is ready for announcement.
    And Vimes wants to post about the draft schedule, displaying the schedule in a tabular format
    Given that Vimes has drafted an update in this project for the public announcement with the schedule in tabular format
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: Vimes wants to send weekly reminders about the schedule, venue and speakers for 2011 expo.
    And Vimes has drafted the copy of the update
    And Vimes has scheduled the update to go out at 9:00 AM each week
    Given that Vimes publishes schedule to send weekly update
    Then the weekly update is sent to everyone who signed up for the 2011 edition
    And the weekly update is sent to everyone who signed up for a past edition

  Scenario: Twoflower wants to be reminded about the date, day and time of the 2011 expo one week before the event
    Given that Twoflower has registered to attend 2011 expo
    Then Twoflower's RSVP should show up on their device calendar with the option to be reminded about 2011 expo one week before

  Scenario: Twoflower has registered to attend 2011 expo and is unable to find the venue and schedule for the 2011 expo amidst all the updates
    And Twoflower wants to search for the venue and schedule notification
    Given that Twoflower has registered to attend 2011 expo
    Then Twoflower should be able to search the venue and schedule updates via search in Updates
