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

  Scenario: Vimes posts a public notice about the venue and facilities. 
    And Vimes is also an editor of the 2011 expo project
    Given that Vimes has drafted an update about the venue, parking and check-in procedure
    And Vimes has published the update
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition

  Scenario: Vimes posts a public notice about the speakers of 2011 expo.      
    Given that Vimes has drafted an update in this project for the public announcement
    And Vimes has added links for each speaker's talk.
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition
    And Twoflower is redirected to the descriptions each time he clicks on the talk links 

  Scenario: Vimes posts a public notice about the schedule for 2011 expo.
    Given that Vimes has drafted an update in this project for the public announcement
    And Vimes has added the schedule in a tabular format in markdown
    Then the update is sent to everyone who signed up for the 2011 edition
    And the update is sent to everyone who signed up for a past edition
    And Twoflower can the see the schedule in a tabular format in the update

  Scenario: Vimes posts a public notice.
    And Vimes has drafted weekly reminders, leading to 2011 expo
    And Vimes has scheduled the reminder updates to go out weekly on Friday at 10 AM
    Given that Vimes schedules the weekly updates
    Then the weekly update is sent to everyone who signed up for the 2011 edition on the schedule day and time
    And the weekly update is sent to everyone who signed up for a past edition on the schedule day and time

  Scenario: Twoflower needs a reminder about 2011 expo one week before.
    Given that Twoflower has registered to attend 2011 expo
    Then Twoflower's RSVP should show up on his device calendar with the option to be reminded about 2011 expo one week before

  Scenario: Twoflower has registered to attend 2011 expo but is unable to find the venue and directions.
    And Twoflower searches for the venue and schedule notification
    Given that Twoflower has registered to attend 2011 expo
    Then Twoflower can search updates to find venue and directions update
