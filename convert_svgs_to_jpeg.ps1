Add-Type -AssemblyName System.Drawing

function New-JpegImage {
    param(
        [string]$Path,
        [int]$Width,
        [int]$Height,
        [ScriptBlock]$DrawAction
    )

    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.Clear([System.Drawing.Color]::FromArgb(248,250,252))

    & $DrawAction $graphics

    $quality = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $quality.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, 90)
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $bitmap.Save($Path, $codec, $quality)

    $graphics.Dispose()
    $bitmap.Dispose()
}

$drawArch = {
    param($g)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(47,79,79), 2)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(31,41,55))
    $fontTitle = New-Object System.Drawing.Font('Arial', 20, [System.Drawing.FontStyle]::Bold)
    $fontText = New-Object System.Drawing.Font('Arial', 16)

    $g.FillRectangle($brush, 70, 110, 180, 120)
    $g.DrawRectangle($pen, 70, 110, 180, 120)
    $g.DrawString('User / Analyst', $fontText, $textBrush, 160, 145, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Natural Language Query', $fontText, $textBrush, 160, 170, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 330, 90, 220, 160)
    $g.DrawRectangle($pen, 330, 90, 220, 160)
    $g.DrawString('NL Retrieval Pipeline', $fontTitle, $textBrush, 440, 125, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Intent Parsing -> Ontology Mapping', $fontText, $textBrush, 440, 150, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Constraint Validation -> Plan Generation', $fontText, $textBrush, 440, 175, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Result Verification', $fontText, $textBrush, 440, 200, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 620, 110, 220, 120)
    $g.DrawRectangle($pen, 620, 110, 220, 120)
    $g.DrawString('Database / Data Layer', $fontText, $textBrush, 730, 145, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('PostgreSQL / SQLAlchemy', $fontText, $textBrush, 730, 170, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 330, 310, 220, 140)
    $g.DrawRectangle($pen, 330, 310, 220, 140)
    $g.DrawString('Monitoring & Validation', $fontTitle, $textBrush, 440, 345, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Semantic Drift Metric', $fontText, $textBrush, 440, 375, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Audit Log + Provenance', $fontText, $textBrush, 440, 400, [System.Drawing.StringFormat]::GenericDefault)

    $g.DrawLine($pen, 250, 170, 330, 170)
    $g.DrawLine($pen, 550, 170, 620, 170)
    $g.DrawLine($pen, 440, 250, 440, 310)
    $g.DrawLine($pen, 440, 450, 440, 470)

    $pen.Dispose(); $brush.Dispose(); $textBrush.Dispose(); $fontTitle.Dispose(); $fontText.Dispose()
}

$drawFlow = {
    param($g)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(37,78,106), 3)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15,23,42))
    $fontTitle = New-Object System.Drawing.Font('Arial', 20, [System.Drawing.FontStyle]::Bold)
    $fontText = New-Object System.Drawing.Font('Arial', 15)

    $g.FillRectangle($brush, 340, 90, 280, 70)
    $g.DrawRectangle($pen, 340, 90, 280, 70)
    $g.DrawString('Receive Natural Language Query', $fontText, $textBrush, 480, 130, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 340, 190, 280, 70)
    $g.DrawRectangle($pen, 340, 190, 280, 70)
    $g.DrawString('Intent Parser Agent', $fontTitle, $textBrush, 480, 230, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Extract Entities & Metrics', $fontText, $textBrush, 480, 250, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 110, 290, 280, 70)
    $g.DrawRectangle($pen, 110, 290, 280, 70)
    $g.DrawString('Ontology Mapper Agent', $fontText, $textBrush, 250, 330, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Align with Schema', $fontText, $textBrush, 250, 350, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 570, 290, 280, 70)
    $g.DrawRectangle($pen, 570, 290, 280, 70)
    $g.DrawString('Constraint Validator Agent', $fontText, $textBrush, 710, 330, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Apply Business Rules', $fontText, $textBrush, 710, 350, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 340, 390, 280, 70)
    $g.DrawRectangle($pen, 340, 390, 280, 70)
    $g.DrawString('Execution Planner Agent', $fontText, $textBrush, 480, 430, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Build Retrieval Plan', $fontText, $textBrush, 480, 450, [System.Drawing.StringFormat]::GenericDefault)

    $g.FillRectangle($brush, 340, 490, 280, 70)
    $g.DrawRectangle($pen, 340, 490, 280, 70)
    $g.DrawString('Result Verifier Agent', $fontText, $textBrush, 480, 530, [System.Drawing.StringFormat]::GenericDefault)
    $g.DrawString('Validate Plausibility', $fontText, $textBrush, 480, 550, [System.Drawing.StringFormat]::GenericDefault)

    $g.DrawLine($pen, 480, 160, 480, 190)
    $g.DrawLine($pen, 480, 260, 250, 290)
    $g.DrawLine($pen, 480, 260, 710, 290)
    $g.DrawLine($pen, 250, 360, 420, 360)
    $g.DrawLine($pen, 710, 360, 550, 360)
    $g.DrawLine($pen, 480, 460, 480, 490)

    $pen.Dispose(); $brush.Dispose(); $textBrush.Dispose(); $fontTitle.Dispose(); $fontText.Dispose()
}

$drawOut = {
    param($g)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(51,65,85), 2)
    $brushPanel = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $brushLine = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(15,118,110), 4)
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15,23,42))
    $fontTitle = New-Object System.Drawing.Font('Arial', 18, [System.Drawing.FontStyle]::Bold)
    $fontText = New-Object System.Drawing.Font('Arial', 14)

    $g.FillRectangle($brushPanel, 40, 90, 420, 420)
    $g.DrawRectangle($pen, 40, 90, 420, 420)
    $g.DrawString('Performance Metrics', $fontText, $textBrush, 60, 122)
    $g.DrawLine($brushLine, 70, 450, 145, 380)
    $g.DrawLine($brushLine, 145, 380, 220, 320)
    $g.DrawLine($brushLine, 220, 320, 295, 260)
    $g.DrawLine($brushLine, 295, 260, 370, 210)
    $g.DrawLine($brushLine, 370, 210, 410, 190)
    $g.DrawString('Iterations →', $fontText, $textBrush, 70, 480)
    $g.DrawString('Accuracy / Drift Trend', $fontText, $textBrush, 60, 140)
    $g.DrawString('0.9', $fontText, $textBrush, 360, 250)
    $g.DrawString('0.7', $fontText, $textBrush, 360, 325)

    $g.FillRectangle($brushPanel, 500, 90, 420, 420)
    $g.DrawRectangle($pen, 500, 90, 420, 420)
    $g.DrawString('Sample Output Log', $fontText, $textBrush, 520, 122)
    $g.DrawString('2026-04-25T13:20:07.341Z | INFO  | IntentParserAgent', $fontText, $textBrush, 520, 160)
    $g.DrawString("Parsed intent: 'Show orders' (0.92)", $fontText, $textBrush, 520, 185)
    $g.DrawString('2026-04-25T13:20:07.387Z | INFO  | OntologyMapperAgent', $fontText, $textBrush, 520, 215)
    $g.DrawString('Matched orders -> sales.order_table', $fontText, $textBrush, 520, 240)
    $g.DrawString('2026-04-25T13:20:07.421Z | INFO  | ConstraintValidatorAgent', $fontText, $textBrush, 520, 270)
    $g.DrawString('All business rules satisfied', $fontText, $textBrush, 520, 295)
    $g.DrawString('2026-04-25T13:20:07.452Z | INFO  | ExecutionPlannerAgent', $fontText, $textBrush, 520, 325)
    $g.DrawString('Generated plan with 3 joins', $fontText, $textBrush, 520, 350)
    $g.DrawString('2026-04-25T13:20:07.498Z | INFO  | ResultVerifierAgent', $fontText, $textBrush, 520, 380)
    $g.DrawString('Plausibility score 0.91, drift 0.12', $fontText, $textBrush, 520, 405)

    $pen.Dispose(); $brushPanel.Dispose(); $brushLine.Dispose(); $textBrush.Dispose(); $fontTitle.Dispose(); $fontText.Dispose()
}

$drawTimeline = {
    param($g)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(51,65,85), 2)
    $brushPanel = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $brushBar = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(37,99,235))
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15,23,42))
    $fontTitle = New-Object System.Drawing.Font('Arial', 20, [System.Drawing.FontStyle]::Bold)
    $fontText = New-Object System.Drawing.Font('Arial', 14)

    $g.FillRectangle($brushPanel, 20, 20, 920, 520)
    $g.DrawRectangle($pen, 20, 20, 920, 520)
    $g.DrawString('Project Timeline', $fontTitle, $textBrush, 40, 58)
    $g.DrawString('Feb 26: Topic Selection & Problem Statement', $fontText, $textBrush, 40, 90)
    $g.FillRectangle($brushBar, 40, 100, 220, 24)
    $g.DrawString('Mar 12: Synopsis Submission', $fontText, $textBrush, 40, 150)
    $g.FillRectangle($brushBar, 40, 160, 150, 24)
    $g.DrawString('Mar 27: Phase 1 (Information Gathering)', $fontText, $textBrush, 40, 210)
    $g.FillRectangle($brushBar, 40, 220, 320, 24)
    $g.DrawString('Apr 28: Phase 2 (Demonstration / Prototype)', $fontText, $textBrush, 40, 260)
    $g.FillRectangle($brushBar, 40, 270, 240, 24)
    $g.DrawString('May 06: Draft Paper Submission', $fontText, $textBrush, 40, 300)
    $g.FillRectangle($brushBar, 40, 310, 180, 24)
    $g.DrawString('May 29: Final Review & Completion', $fontText, $textBrush, 40, 350)
    $g.FillRectangle($brushBar, 40, 360, 220, 24)
    $g.DrawString('Jun 01: Final Submission', $fontText, $textBrush, 40, 400)
    $g.FillRectangle($brushBar, 40, 410, 160, 24)
    $g.DrawString('Jun 15: Semester End Examination', $fontText, $textBrush, 40, 450)
    $g.FillRectangle($brushBar, 40, 460, 200, 24)

    $pen.Dispose(); $brushPanel.Dispose(); $brushBar.Dispose(); $textBrush.Dispose(); $fontTitle.Dispose(); $fontText.Dispose()
}

New-JpegImage 'docs/images/architecture_diagram.jpg' 960 560 $drawArch
New-JpegImage 'docs/images/workflow_flowchart.jpg' 960 660 $drawFlow
New-JpegImage 'docs/images/output_analysis_mockup.jpg' 960 560 $drawOut
New-JpegImage 'docs/images/timeline_gantt.jpg' 960 560 $drawTimeline
Write-Host 'JPEG files created successfully.'
