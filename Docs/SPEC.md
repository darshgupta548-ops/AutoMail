# AUTO-MAIL — Software Specification

## 1. Project Overview
**Project Name:** AUTO-MAIL  
**Full Name:** Automated Responsive Mail Generator

AUTO-MAIL converts an event poster plus event information into a polished, responsive HTML email and delivers the finished email to an authorized IT/Admin recipient.

The system is designed for college clubs and event organizers who already have the event material but do not want to spend hours manually designing and adapting emails.

## 2. Problem Statement
Manual event-email creation can require extracting details from posters/messages, rewriting copy, arranging logos and images, adapting layouts for mobile, and testing the final result in a real inbox. Existing drag-and-drop builders reduce some of this work but can still require substantial manual effort and may produce mobile layouts that differ from the intended design.

AUTO-MAIL automates creation while retaining human approval.

## 3. Users
**Primary:** college club members, event organizers, publicity/technical teams.  
**External actor:** IT/Admin, which receives and distributes the approved email to students.

## 4. Product Goal
> Provide the event information once; obtain a professional, responsive email with minimal manual design effort.

## 5. Inputs
- Event poster
- Pasted event/WhatsApp message
- Manual/corrected details: event name, organization, date, time, venue, registration URL, notes, tone

User-provided corrections take precedence over conflicting extracted information.

## 6. Functional Requirements
**FR-01:** Accept poster, message, and manual event input.  
**FR-02:** Upload email assets to image hosting and obtain HTTPS URLs.  
**FR-03:** Sense Maker combines poster, message, and details into structured email context.  
**FR-04:** Human review is required before email generation.  
**FR-05:** Generate email-safe responsive HTML.  
**FR-06:** Support desktop and mobile layouts.  
**FR-07:** Support Light and Dark email themes.  
**FR-08:** Human review of generated email is required.  
**FR-09:** Produce a complete HTML email body suitable for the delivery service.  
**FR-10:** Send the approved email through the selected mail service.  
**FR-11:** Support sending a test email to a human tester.  
**FR-12:** Send the approved final email to IT/Admin.

AUTO-MAIL does not maintain the student mailing list or perform institution-wide distribution.

## 7. Human-in-the-Loop
### Gate 1 — Context Review
Verify facts, completeness, tone, copy, and CTA.

### Gate 2 — Email Review
Verify layout, typography, images, theme, hierarchy, and mobile preview.

### Gate 3 — Real Inbox Test
Verify the actual received email on a real client/device. Rendering failure returns the workflow to Email Maker.

## 8. Output
The primary output is **a real rendered HTML email delivered to the authorized IT/Admin recipient**.

Raw HTML may exist internally for preview/debugging but is not the primary user-facing deliverable.

## 9. Non-Functional Requirements
- **Reliability:** manual details remain available if AI fails.
- **Responsiveness:** output must be tested on desktop and mobile.
- **Usability:** creation should take minutes rather than hours.
- **Maintainability:** reusable templates/components, not arbitrary AI-generated HTML.
- **Security:** secrets remain server-side; uploads are validated.
- **Consistency:** approved context + theme should produce consistent structure.
- **Auditability:** workflow state should indicate generated, reviewed, tested, and sent stages.

## 10. MVP
### Must Have
Poster upload; message/details input; image hosting; AI context generation; context review; responsive HTML generation; Light/Dark themes; desktop/mobile preview; real test email; final send to IT/Admin.

### Out of Scope
Bulk mailing; student/contact database; analytics; campaign scheduling; drag-and-drop editor; template marketplace; enterprise email management; guaranteed identical rendering across every email client.

## 11. Future Scope
- In-email theme switching where supported
- Saved brand kits
- Multiple reusable templates
- Richer asset management
- Direct institutional integrations
- Scheduling and analytics
- Campaign management

## 12. Success Criteria
A user can go from poster + event information to approved, tested, and delivered IT/Admin email through one coherent workflow.
