# PriceWatch: Product List Dashboard

## Vibe
Premium monitoring dashboard with Kinetic Terminal aesthetic. Dark background, neon accents, minimal borders, high information density. Professional and technical monitoring interface.

## Design System
- **Background**: `#0e0e0f` (dark charcoal)
- **Primary Accent (Price Drops)**: `#a1ffc2` (neon green)
- **Secondary Accent (Price Increases)**: `#ff7168` (red-orange)
- **Tertiary Accent (Sparklines/Info)**: `#69daff` (cyan blue)
- **Text**: High contrast white with subtle gray hierarchy
- **Status Indicators**: Dim green (#a1ffc2 at 40% opacity)

## Page Structure
Display a table titled "TRACKED PRODUCTS" showing:
- **ID**: Numeric product ID
- **Product Name**: Left-aligned primary text
- **Current Price**: Right-aligned, colored green if price dropped, red if increased
- **Previous Price**: Right-aligned, gray muted text  
- **Change**: Right-aligned, showing -$XX.XX (-Y%) in green for drops, red for increases
- **Trend Sparkline**: Inline micro-chart using Unicode blocks in cyan
- **Status**: Single colored dot (green for active)

## Layout Details
- Dark charcoal background (#0e0e0f)
- Table borders: Subtle dark gray, very thin
- Rows: Alternating background opacity (base + 5% lighter alternate)
- Minimal spacing and footer
- Compact, technical, monitoring-dashboard aesthetic
