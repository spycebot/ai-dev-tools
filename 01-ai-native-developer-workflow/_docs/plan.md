# Household Chore Manager - Project Plan

## Overview
A Django web application for managing shared household chores within a family. The tool maintains a central list of chores, tracks who completed each chore and when, and allows anyone on the home network to contribute.

## Users & Access
- **Target Users**: Family members at home
- **Access**: Available to anyone on the home network
- **Authentication**: Not required
- **Permissions**: 
  - Anyone can add new chores
  - Anyone can mark chores as complete

## Core Features

### 1. Chore List
- Display all chores in a shared list
- Show chore status (pending/completed)
- Sort and filter by priority

### 2. Chore Properties
Each chore has:
- **Description**: What needs to be done
- **Priority**: High, Medium, or Low
- **Status**: Pending or Completed
- **Completion History**: Who completed it and when

### 3. Add Chores
- Anyone can add a new chore to the list
- Required fields: description, priority
- Form-based input

### 4. Complete Chores
- Mark chores as complete
- Completer enters their name (text input)
- System records timestamp automatically
- Completed chore moves to history

## Technology Stack
- **Backend**: Django
- **Platform**: Web application
- **Hosting**: Home network accessible

## Out of Scope (MVP)
- User authentication and login
- Chore assignment or scheduling
- Recurring/scheduled chores
- Chore deadlines
- User profiles or roles
- Admin panel (initially)

## Data Model
- **Chore**
  - id
  - description
  - priority (CHOICES: high, medium, low)
  - created_at
  - completed_at (nullable)
  - completed_by (nullable)
  - status

## User Interface
- Simple, home-network accessible web interface
- List view of all chores
- Form to add new chores
- Button/action to mark chore as complete
- Completion confirmation requiring name entry
