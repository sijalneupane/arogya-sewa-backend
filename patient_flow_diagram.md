# Patient Flow State Diagram

```mermaid
stateDiagram-v2
    [*] --> HomePage
    
    HomePage --> ViewDoctors: Browse Doctors
    
    ViewDoctors --> ViewDoctorProfile: Select Doctor
    ViewDoctors --> HomePage: Go Back
    
    ViewDoctorProfile --> ViewAvailability: View Availability
    ViewDoctorProfile --> ViewDoctors: Go Back
    
    ViewAvailability --> Login: Book Appointment
    ViewAvailability --> ViewDoctors: Go Back
    
    Login --> CreateAppointment: Credentials Valid
    Login --> Login: Invalid Credentials
    
    CreateAppointment --> AppointmentConfirmed: Payment Success
    CreateAppointment --> ViewAvailability: Cancel Booking
    
    AppointmentConfirmed --> ViewDoctors: Browse More Doctors
    AppointmentConfirmed --> Logout: End Session
    
    Logout --> HomePage: Redirect Home
    
    note right of HomePage
        Landing page
        No login required
    end note
    
    note right of ViewDoctors
        Browse available doctors
        Filter by hospital/department
    end note
    
    note right of ViewDoctorProfile
        View doctor details and bio
        See specialization
    end note
    
    note right of ViewAvailability
        See available appointment slots
        No login required yet
    end note
    
    note right of Login
        User enters email and password
        Only required to book
    end note
    
    note right of CreateAppointment
        Patient creates appointment
        Pays advance fee via Khalti
    end note
    
    note right of Logout
        End current session
        Clears tokens
    end note
```

## State Descriptions

| State | Description |
|-------|-------------|
| **HomePage** | Landing page - users can start browsing without login |
| **ViewDoctors** | Browse and filter available doctors by hospital/department |
| **ViewDoctorProfile** | View detailed doctor information, specialization, and bio |
| **ViewAvailability** | See available appointment time slots (no login required) |
| **Login** | User enters credentials only when they want to book an appointment |
| **CreateAppointment** | Book appointment and process Khalti payment |
| **AppointmentConfirmed** | Appointment successfully created and payment confirmed |
| **Logout** | End user session and redirect to home page |
