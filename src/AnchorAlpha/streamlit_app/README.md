# AnchorAlpha Streamlit Application

This directory contains the Streamlit web application for the AnchorAlpha Momentum Screener.

## Components

### Core Files

- **`app.py`** - Main application entry point for running with Streamlit
- **`momentum_dashboard.py`** - Main dashboard class and application logic
- **`ui_components.py`** - Reusable UI components (selectors, tables, filters)
- **`styling.py`** - Dark theme styling and branding components
- **`data_loader.py`** - S3 data loading with caching (from task 8)
- **`data_transforms.py`** - Data transformation utilities (from task 8)
- **`cache_manager.py`** - Caching functionality (from task 8)

### Test Files

- **`test_ui_components.py`** - Test script to verify UI components functionality
- **`example_usage.py`** - Example usage of data loading components

## Features Implemented (Task 9)

### 1. Dark Mode Theme
- Navy blue (#001f3f) primary background
- Gold (#FFD700) accent color for headers and highlights
- Slate gray (#708090) for secondary text
- Professional institutional styling

### 2. AnchorAlpha Branding
- Minimalist anchor (⚓) and alpha (α) logo
- Custom typography with serif headers
- Consistent color scheme throughout

### 3. UI Components

#### TierSelector
- Market cap tier filtering
- Options: $100B-$200B, $200B-$500B, $500B-$1T, $1T+
- Dynamic filtering based on available data

#### TimeframeSelector  
- Momentum timeframe selection
- Options: 7 Days, 30 Days, 60 Days, 90 Days
- Supports "All Timeframes" view

#### StockRankingTable
- Sortable columns for stock rankings
- Momentum percentages with color coding
- AI summary availability indicators
- Interactive stock selection for details

#### FilterControls
- Advanced filtering options
- Momentum range sliders
- AI summary availability filter
- Positive momentum only option

### 4. Dashboard Layout
- Responsive design for desktop and mobile
- Sidebar controls for filtering
- Tabbed interface for different views
- Expandable sections for detailed data

### 5. Data Visualization
- Cross-tier performance comparison
- Tier-by-tier breakdown tables
- Top performers overview
- Momentum heatmap data preparation

## Usage

### Running the Application

```bash
# From the project root
streamlit run AnchorAlpha/src/AnchorAlpha/streamlit_app/app.py
```

### Testing Components

```bash
# Test UI components functionality
cd AnchorAlpha/src/AnchorAlpha/streamlit_app
python test_ui_components.py
```

### Component Testing

```bash
# Test data loading components
cd AnchorAlpha/src/AnchorAlpha/streamlit_app  
python example_usage.py
```

## Dashboard Views

### 1. Overview Mode (All Tiers & Timeframes)
- Cross-tier comparison tables
- Tier breakdown summaries
- Top performers across all categories

### 2. Timeframe View (Specific timeframe, all tiers)
- Performance comparison across tiers for selected timeframe
- Top performers by tier for the timeframe

### 3. Tier View (Specific tier, all timeframes)
- Performance summary across timeframes for selected tier
- Top performers by timeframe for the tier

### 4. Specific View (Specific tier & timeframe)
- Detailed stock rankings
- Interactive stock selection
- AI summary display
- Performance statistics

## Styling Features

### Color Coding
- **Positive momentum**: Green (#28a745)
- **Negative momentum**: Red (#dc3545)
- **Neutral momentum**: Slate gray (#708090)

### Tier Badges
- **$100B-$200B**: Green badge
- **$200B-$500B**: Orange badge  
- **$500B-$1T**: Red badge
- **$1T+**: Gold badge

### Interactive Elements
- Hover effects on buttons
- Loading spinners with anchor branding
- Responsive metric cards
- Styled info/warning/error boxes

## Dependencies

The Streamlit app requires:
- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `boto3` - AWS S3 integration (via data_loader)
- Other dependencies from the main AnchorAlpha package

## Integration

The Streamlit app integrates with:
- **S3 Data Storage** - Loads processed momentum data
- **Lambda Processing** - Displays results from daily processing
- **Caching System** - Optimizes data loading performance
- **Error Handling** - Graceful degradation when data unavailable

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **7.1**: Dark mode interface with navy blue, gold, and slate gray colors ✓
- **7.2**: AnchorAlpha branding with anchor and alpha logo elements ✓  
- **7.3**: Clean, institutional-grade styling for professional analysis ✓
- **7.4**: Smooth, responsive user experience optimized for data consumption ✓

The UI components provide a complete, professional interface for viewing momentum analysis results with institutional-grade styling and branding.