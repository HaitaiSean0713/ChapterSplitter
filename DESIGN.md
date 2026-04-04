# 專案設計系統：Chapter Splitter Tool

## 核心設定 (Core Settings)
*   **Color Mode**: LIGHT
*   **Font**: INTER (Headline/Body/Label 皆使用 INTER)
*   **Roundness**: ROUND_EIGHT
*   **Primary Custom Color**: #0071E3

## 顏色定義摘要 (Named Colors)
*   `primary`: #0059b5
*   `primary_container`: #0071e3
*   `background`: #fcf8fb
*   `surface_container_lowest` (浮動卡片/啟用狀態): #ffffff
*   `surface_container_low` (標準表面): #f6f3f5
*   `surface_container_high` (微凹區域): #eae7ea
*   `on_surface` (文字): #1b1b1d
*   `outline_variant` (幽靈邊框): #c1c6d6

---

# Design System Strategy: The Precision Curator

## 1. Overview & Creative North Star
The visual language of this design system is guided by a Creative North Star we call **"The Precision Curator."** It is an editorial-first approach to utility, designed specifically for the task of parsing and organizing content. 

Rather than a standard "tool" aesthetic that feels cluttered and mechanical, this system treats digital content like a high-end gallery. It breaks the "template" look by utilizing intentional asymmetry—placing heavy, high-contrast typography against expansive, "silent" white space. We reject rigid grids in favor of a flow that feels rhythmic and intentional, where the absence of an element is just as important as its presence.

## 2. Colors & Surface Logic
The palette is rooted in a monochromatic foundation with a singular, high-performance accent. It uses tonal depth to communicate hierarchy rather than structural ornamentation.

### Tonal Tokens
*   **Primary (Action):** `#0059b5` (Primary) / `#0071e3` (Primary Container)
*   **Background:** `#fcf8fb`
*   **Surface Tiers:**
    *   `surface-container-lowest`: `#ffffff` (Floating cards/Active states)
    *   `surface-container-low`: `#f6f3f5` (Standard surface)
    *   `surface-container-high`: `#eae7ea` (Subtle recessed areas)
*   **Text:** `#1b1b1d` (On-Surface)

### The "No-Line" Rule
Explicitly, designers are **prohibited from using 1px solid borders** to section content. Boundaries must be defined solely through background color shifts. For example, a chapter card (`surface-container-lowest`) should sit on a workspace background (`surface-container-low`). This creates a soft, modern transition that mimics natural light rather than a CAD drawing.

### Glass & Gradient Implementation
While the system is "flat," we introduce "Visual Soul" through:
*   **Signature Textures:** Main Action buttons should utilize a subtle gradient from `primary` to `primary_container`. This prevents the blue from looking "plastic" and adds a professional, backlit polish.
*   **Glassmorphism:** Floating navigation bars or playback controls should use a semi-transparent `surface` color with a 20px backdrop blur. This allows the chapter content to "ghost" behind the controls, creating a sense of three-dimensional space.

## 3. Typography: Editorial Authority
We utilize a high-contrast scale where the weight of the font does the work of a divider.

*   **Display (Display-LG/MD):** Used for the primary tool state (e.g., "Untitled Video"). These should be massive, bold, and slightly tracked-in (-0.02em) to feel like a magazine masthead.
*   **Headlines (Headline-SM):** Used for chapter titles. Strong and authoritative.
*   **Body (Body-LG/MD):** To achieve the "Apple-inspired" lightness, body text must use a lighter weight (300 or 400). It should feel "airy" and secondary to the data.
*   **Labels (Label-MD):** Used for timestamps. These are the "metadata" of the system and should be in `on_surface_variant` (#414753) to reduce visual noise.

## 4. Elevation & Depth
Hierarchy is achieved through **Tonal Layering**—the physical stacking of surfaces.

*   **The Layering Principle:** Place a `surface-container-lowest` card on a `surface-container-low` section to create a soft, natural lift. This is "Zero-Shadow Elevation."
*   **Ambient Shadows:** When a card must "float" (e.g., during a drag-and-drop split), use an extra-diffused shadow: `0 12px 40px rgba(27, 27, 29, 0.04)`. The shadow color is a tinted version of the `on-surface` token, not a neutral grey, to mimic ambient light.
*   **The "Ghost Border":** If accessibility requires a stroke (e.g., in high-contrast modes), use the `outline-variant` token at **15% opacity**. A 100% opaque border is considered a failure of the design system's elegance.

## 5. Components

### Primary Split Button
The cornerstone of the tool. 
*   **Style:** `primary` background, `on_primary` text.
*   **Radius:** 12px (`md`).
*   **Motion:** On hover, the background should shift to `primary_container`. No heavy shadows; just a subtle color "glow."

### Chapter Cards
*   **Structure:** No borders. `surface-container-lowest` background. 16px (`lg`) corner radius.
*   **Spacing:** 24px internal padding to ensure the "Precision Curator" look.
*   **Separation:** Instead of dividers, use 16px of vertical whitespace between cards.

### The Timeline / Input Fields
*   **Inputs:** Minimalist. No box around the input. Only a subtle `outline-variant` bottom-weighted line (Ghost Border style) that becomes `primary` blue and 2px thick on focus.
*   **Chips:** Use for "Tags" or "Auto-detected" splits. 8px (`sm`) radius. Background: `surface-container-high`.

### Lists & Dividers
**Divider Prohibiton:** Never use a horizontal rule `<hr>`. Use a background color change or a 32px vertical gap.

## 6. Do’s and Don’ts

### Do:
*   **Embrace Asymmetry:** Align the chapter titles to the left and timestamps to the extreme right, leaving a "void" in the middle to emphasize the width of the canvas.
*   **Use SF Symbols:** Keep icons ultra-thin (Light or Regular weight) to match the light body text.
*   **Generous Spacing:** If a layout feels "busy," double the whitespace. The system relies on "breathing room."

### Don’t:
*   **Don't use 100% black:** Always use `on-surface` (#1b1b1d) for text. Pure black is too harsh for an editorial experience.
*   **Don't use standard shadows:** Avoid the `0 2px 4px` default. It looks "web 2.0." Use our Tonal Layering or Ambient Shadows.
*   **Don't crowd the edges:** Maintain a minimum of 40px margin around the primary workspace containers.
