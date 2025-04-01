# Media Storage and Photo Management

## Overview

This application uses Cloudinary as its image hosting solution for both boulder photos and competition-submitted images. This document outlines our storage architecture, security model, and optimization strategies.

## Storage Structure

All media is organized in Cloudinary using the following folder structure:

```
boulder-comp/
├── boulder-photos/
│   ├── crag-name-1/
│   │   ├── sector-name-1/
│   │   │   ├── boulder_name_photo_id_hash.jpg
│   │   │   └── ...
│   │   ├── sector-name-2/
│   │   │   └── ...
│   │   └── ...
│   ├── crag-name-2/
│   │   └── ...
│   └── ...
├── competition-photos/
    ├── competition-name-1/
    │   ├── uploader_name_hash.jpg
    │   └── ...
    ├── competition-name-2/
    │   └── ...
    └── ...
```

This structure provides several benefits:
1. **Logical Organization**: Photos are grouped by type, crag/competition, and sector (for boulder photos)
2. **Security**: Access control can be applied at different levels of the hierarchy
3. **Performance**: Easier lookup and management of photos
4. **Traceability**: Photos can be easily associated with their source

## Image Optimization with Cloudinary

Cloudinary provides advanced image optimization capabilities:

1. **Adaptive Format Delivery**:
   - Automatically serves WebP or AVIF to supporting browsers
   - Falls back to JPEG/PNG for older browsers
   - Reduces file sizes by 30-70% compared to traditional formats

2. **Automatic Quality Optimization**:
   - Uses perceptual quality algorithms to reduce file size without visible quality loss
   - Adapts quality settings based on image content

3. **Responsive Delivery**:
   - Generates multiple resolution variants automatically
   - Delivers appropriate size based on device and viewport
   - Reduces data usage on mobile devices

4. **Global CDN Integration**:
   - Faster loading times worldwide
   - Reduced latency in remote areas
   - Critical for competitions in areas with limited connectivity

## Access Control and Security

### Boulder Photos

Boulder photos are accessible to:
1. **All Users**: Public access is granted for boulder photos
2. **API Backend**: Full access for management operations

### Competition Photos

Competition photos use a more restricted access model:

1. **Administrators**: 
   - Full access to view, approve, and feature photos
   - Can moderate inappropriate content

2. **Competition Participants**: 
   - Can submit photos to their assigned competitions
   - Can view approved photos from their competitions

3. **Public Users**:
   - Can only see approved and featured photos

### Technical Implementation

Access control is implemented through:

1. **Database Filtering**:
   - Competition photos are filtered based on approval status and user roles
   - Only approved photos are returned to non-admin users

2. **API Authorization**:
   - Photo approval/featuring endpoints require admin authentication
   - Photo submission endpoints verify participant status

3. **Content Moderation**:
   - Automatic content moderation via Cloudinary's AWS Rekognition integration
   - Admin review interface for flagged content

## Photo Upload Flow

### Boulder Photos

Boulder photos follow this upload process:
1. Images are initially scraped from source websites
2. The API processes and uploads these images to Cloudinary
3. Image metadata is stored in the database, linking to boulder records

### Competition Photos

For user-submitted competition photos:
1. Users upload photos through the frontend application
2. The API receives the temporary photo URL
3. Photos are uploaded to Cloudinary with moderation enabled
4. Database records are created with pending approval status
5. Administrators review and approve photos
6. Approved photos appear in competition galleries

## Technical Implementation

The media storage system is implemented through:

1. **CloudinaryUploader Class**:
   - Handles all upload operations
   - Manages folder organization
   - Applies appropriate transformations and tags

2. **REST API Endpoints**:
   - `/upload-boulder-photos/{crag_name}`: Upload boulder photos for a crag
   - `/upload-competition-photos/{competition_id}`: Upload user submissions
   - `/competition-photos/{competition_id}`: Retrieve competition photos
   - `/competition-photos/{photo_id}/approve`: Approve/reject photos
   - `/competition-photos/{photo_id}/feature`: Feature special photos

3. **Database Integration**:
   - Tables track Cloudinary URLs and public IDs
   - Tracks approval status and moderation information
   - Links photos to their associated entities (boulders/competitions)

This implementation provides a robust, scalable, and secure solution for managing both boulder photos and user-submitted competition photos.

## Testing Access Control

You can test the competition photo access control by:

1. Creating test users with different roles (admin, participant)
2. Registering them for different competitions
3. Verifying they can only access photos from their assigned competitions 