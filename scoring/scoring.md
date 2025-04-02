# Climbing Competition Scoring System

This document describes the scoring system used for the climbing competition platform, including the calculation methods, processes, and considerations for each scoring category.

## Overview

The scoring system supports two main competition categories:

1. **Marathon** - Team-based scoring that emphasizes volume, team collaboration, and diverse climbing achievements
2. **Boulder Beasts** - Individual-based scoring that focuses on the most difficult climbs achieved by each participant

## Scoring Process Flow

The scoring calculation happens in the following general sequence:

1. Competition data and all ascents are retrieved from the database
2. Raw data is saved for audit purposes
3. Based on the competition categories, scores are calculated for Marathon and/or Boulder Beasts
4. Detailed calculation data is saved at each step
5. Final rankings are stored in both JSON files and the database
6. Leaderboards are made available through the API

## Marathon Scoring Components

Marathon scoring is designed for teams and includes several components:

### 1. Base Score

- Each ascent contributes points based on the difficulty grade
- All team members' ascents are combined for the team's base score

### 2. Volume Score

- Teams receive bonus points for the total volume of ascents
- Volume bonuses follow a tiered structure based on the number of ascents

### 3. Unique Ascent Score

- Teams receive points for climbing a diverse set of routes
- Calculated based on the number of unique routes completed by the team

### 4. Team Ascent Bonus

- Teams earn bonus points when multiple team members complete the same route
- The more team members who climb a given route, the higher the bonus

### 5. Master Grade Bonus

- Teams leading in the most ascents at a particular grade receive bonus points
- Rewards teams that dominate specific difficulty levels

### 6. Normalization

- Final scores are normalized based on team size to ensure fair competition between teams of different sizes

## Boulder Beasts Scoring Components

Boulder Beasts focuses on individual achievement in terms of difficulty:

### 1. Top Grade Score

- Participants are primarily scored based on their top 5 most difficult climbs
- Higher grades earn significantly more points

### 2. Bonus Points

- Additional points may be awarded for special achievements or milestones
- For example, completing a certain number of climbs at a specific difficulty

## Grade Point System

The scoring system assigns point values to each climbing grade:

- VB: 10 points
- V0: 20 points
- V1: 30 points
- V2: 40 points
- V3: 60 points
- V4: 80 points
- V5: 100 points
- V6: 120 points
- V7: 140 points
- V8: 160 points
- V9: 180 points
- V10+: 200+ points

Higher grades receive exponentially more points to reward difficulty achievement.

## Calculation Storage

For each calculation, the system stores:

1. Raw input data (ascents, competition details)
2. Detailed calculation breakdowns
3. Component scores for transparency
4. Final rankings and leaderboards

This allows for:
- Auditing calculations
- Resolving disputes
- Analyzing competition patterns
- Improving the scoring algorithm over time

## API Endpoints

The scoring system exposes several API endpoints:

- `/scoring/calculate/{comp_id}` - Trigger score calculation for a competition
- `/scoring/status/{task_id}` - Check the status of a calculation task
- `/scoring/rankings/{comp_id}` - Get raw ranking data for a competition
- `/scoring/leaderboard/{competition_id}` - Get formatted leaderboard data
- `/scoring/leaderboard-with-models/{competition_id}` - Get typed leaderboard data

## Considerations and Edge Cases

The scoring system accounts for various special cases:

1. **Team Size Differences** - Normalization ensures fair competition between teams of different sizes
2. **Grade Conversion** - The system can handle different grading systems through conversion
3. **Dispute Resolution** - Detailed calculation storage allows for auditing and resolving disputes
4. **Zero Ascents** - Proper handling of teams or participants with no recorded ascents
5. **Competition Categories** - Flexibility to enable/disable different competition categories

## Implementation Details

The scoring system is implemented using:

- Asynchronous task processing for handling long calculations
- JSON storage for detailed calculation auditing
- Database storage for quick access to rankings
- Pydantic models for type safety and validation
- Supabase for data storage and retrieval

## Future Improvements

Potential enhancements to the scoring system:

1. Real-time leaderboard updates during competitions
2. Advanced analytics and visualizations
3. Machine learning-based scoring predictions
4. Additional competition formats and scoring methods
5. Performance optimizations for very large competitions 