Attribute VB_Name = "modStandaloneSolver"
Option Explicit

Private Function GetModelSheet() As Worksheet
    Dim sheetName As String
    sheetName = "Solver" & ChrW(26368) & ChrW(20339) & ChrW(21270)
    Set GetModelSheet = ThisWorkbook.Worksheets(sheetName)
End Function

Public Sub RunProcurementSolver()
    Dim ws As Worksheet
    Dim changingCells As Range
    Dim resultCode As Variant
    Dim solveSucceeded As Boolean

    On Error GoTo SolverError
    Set ws = GetModelSheet()

    If Not IsNumeric(ws.Range("B5").Value) Then
        MsgBox "Enter a valid positive USD/TWD exchange rate in B5.", vbExclamation, "Solver"
        Exit Sub
    End If

    If CDbl(ws.Range("B5").Value) <= 0 Then
        MsgBox "Enter a valid positive USD/TWD exchange rate in B5.", vbExclamation, "Solver"
        Exit Sub
    End If

    If Not IsDate(ws.Range("B6").Value) Then
        MsgBox "Enter a valid latest-arrival date in B6.", vbExclamation, "Solver"
        Exit Sub
    End If

    If Application.WorksheetFunction.Count(ws.Range("C11:C15")) <> 5 Then
        MsgBox "Enter all five demand quantities in C11:C15.", vbExclamation, "Solver"
        Exit Sub
    End If

    If Application.WorksheetFunction.Min(ws.Range("C11:C15")) < 0 Then
        MsgBox "Demand quantities cannot be negative.", vbExclamation, "Solver"
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationAutomatic

    ws.Activate
    ws.Range("E20:E35").Value = 0
    ws.Range("N40:O42").Value = 0
    Set changingCells = Union(ws.Range("E20:E35"), ws.Range("N40:O42"))
    Application.CalculateFull

    Application.Run "Solver.xlam!SolverReset"
    Application.Run "Solver.xlam!SolverOk", _
                    ws.Range("G5"), _
                    2, _
                    0, _
                    changingCells, _
                    2, _
                    "Simplex LP"

    ' Demand balance.
    Application.Run "Solver.xlam!SolverAdd", ws.Range("T11:T15"), 2, 0

    ' Recommended purchase quantities.
    Application.Run "Solver.xlam!SolverAdd", ws.Range("E20:E35"), 4
    Application.Run "Solver.xlam!SolverAdd", ws.Range("E20:E35"), 3, 0
    Application.Run "Solver.xlam!SolverAdd", ws.Range("E20:E35"), 1, ws.Range("F20:F35")

    ' Supplier-use and free-shipping flags.
    Application.Run "Solver.xlam!SolverAdd", ws.Range("N40:O42"), 5
    Application.Run "Solver.xlam!SolverAdd", ws.Range("P40:P42"), 3, 0
    Application.Run "Solver.xlam!SolverAdd", ws.Range("Q40:R42"), 3, 0
    Application.Run "Solver.xlam!SolverAdd", ws.Range("O40:O42"), 1, ws.Range("N40:N42")

    resultCode = Application.Run("Solver.xlam!SolverSolve", True)

    Select Case CLng(resultCode)
        Case 0, 1, 2, 14
            Application.Run "Solver.xlam!SolverFinish", 1
            solveSucceeded = True
        Case 5
            MsgBox "No feasible solution was found. Check demand, stock, and the latest-arrival date.", vbExclamation, "Solver"
        Case 7
            MsgBox "Solver reports that the model is not linear. Confirm that Simplex LP is available.", vbExclamation, "Solver"
        Case Else
            MsgBox "Solver stopped with result code " & CStr(resultCode) & ".", vbExclamation, "Solver"
    End Select

SafeExit:
    Application.EnableEvents = True
    Application.ScreenUpdating = True

    If solveSucceeded Then
        ws.Activate
        ws.Range("A18").Select
        MsgBox "Optimization complete. The orange cells E20:E35 contain the recommended purchase quantities.", vbInformation, "Solver"
    End If
    Exit Sub

SolverError:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "Solver could not run. Confirm that the Solver Add-in is enabled." & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, vbCritical, "Solver"
End Sub

Public Sub InstallSolverButton()
    Dim ws As Worksheet
    Dim btn As Button
    Dim targetArea As Range

    On Error GoTo ButtonError
    Set ws = GetModelSheet()
    Set targetArea = ws.Range("J4:K6")

    On Error Resume Next
    ws.Buttons("btnRunStandaloneSolver").Delete
    On Error GoTo ButtonError

    Set btn = ws.Buttons.Add(targetArea.Left, targetArea.Top, targetArea.Width, targetArea.Height)
    With btn
        .Name = "btnRunStandaloneSolver"
        .Caption = "Run Solver"
        .OnAction = "'" & ThisWorkbook.Name & "'!RunProcurementSolver"
    End With

    MsgBox "The Run Solver button has been added to the Solver sheet.", vbInformation, "Solver"
    Exit Sub

ButtonError:
    MsgBox "The button could not be added." & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, vbCritical, "Solver"
End Sub
