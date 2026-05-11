param(
    [string]$GtFile,
    [string]$EstFile
)

# ============================================================
# 读取轨迹文件
# ============================================================
function Read-Traj {
    param([string]$path)
    $dict = @{}
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $p = $line -split '\s+'
            if ($p.Count -ge 4) {
                $ts = [double]$p[0]
                if (-not $dict.ContainsKey($ts)) {
                    $dict[$ts] = @([double]$p[1], [double]$p[2], [double]$p[3])
                }
            }
        }
    }
    return $dict
}

# ============================================================
# 3x3 矩阵工具函数
# ============================================================
function Mat-Mul($A, $B) {
    $R = @(@(0,0,0),@(0,0,0),@(0,0,0))
    for ($i=0; $i -lt 3; $i++) {
        for ($j=0; $j -lt 3; $j++) {
            $s = 0.0
            for ($k=0; $k -lt 3; $k++) { $s += $A[$i][$k] * $B[$k][$j] }
            $R[$i][$j] = $s
        }
    }
    return $R
}

function Mat-Trans($A) {
    $R = @(@(0,0,0),@(0,0,0),@(0,0,0))
    for ($i=0; $i -lt 3; $i++) {
        for ($j=0; $j -lt 3; $j++) { $R[$i][$j] = $A[$j][$i] }
    }
    return $R
}

function Mat-VecMul($A, $v) {
    return @(
        $A[0][0]*$v[0]+$A[0][1]*$v[1]+$A[0][2]*$v[2],
        $A[1][0]*$v[0]+$A[1][1]*$v[1]+$A[1][2]*$v[2],
        $A[2][0]*$v[0]+$A[2][1]*$v[1]+$A[2][2]*$v[2]
    )
}

function Mat-Det($A) {
    return $A[0][0]*($A[1][1]*$A[2][2]-$A[1][2]*$A[2][1]) -
           $A[0][1]*($A[1][0]*$A[2][2]-$A[1][2]*$A[2][0]) +
           $A[0][2]*($A[1][0]*$A[2][1]-$A[1][1]*$A[2][0])
}

function Diag-Mat($d) {
    return @(@($d,0,0),@(0,$d,0),@(0,0,$d))
}

function Eye3 { return @(@(1,0,0),@(0,1,0),@(0,0,1)) }

# ============================================================
# 3x3 实对称矩阵特征分解 (Jacobi 旋转法)
# 返回: @(特征值数组, 特征向量矩阵)
# ============================================================
function Eigen-Decomp($M) {
    $n = 3
    $A = @(); for($i=0;$i -lt $n;$i++){ $A += ,@($M[$i][0],$M[$i][1],$M[$i][2]) }
    $V = Eye3
    for ($iter = 0; $iter -lt 200; $iter++) {
        # 找最大非对角元
        $maxVal = 0.0; $p = 0; $q = 1
        for ($i=0; $i -lt $n; $i++) {
            for ($j=$i+1; $j -lt $n; $j++) {
                $av = [Math]::Abs($A[$i][$j])
                if ($av -gt $maxVal) { $maxVal = $av; $p = $i; $q = $j }
            }
        }
        if ($maxVal -lt 1e-12) { break }

        # 计算旋转角度
        $theta = 0.0
        if ([Math]::Abs($A[$p][$p] - $A[$q][$q]) -lt 1e-15) {
            $theta = [Math]::PI / 4.0
        } else {
            $theta = 0.5 * [Math]::Atan2(2.0 * $A[$p][$q], $A[$p][$p] - $A[$q][$q])
        }
        $c = [Math]::Cos($theta)
        $s = [Math]::Sin($theta)

        # 构造 Givens 旋转矩阵 G
        $G = Eye3; $G[$p][$p] = $c; $G[$q][$q] = $c; $G[$p][$q] = -$s; $G[$q][$p] = $s

        # A = G^T A G
        $A = Mat-Mul (Mat-Trans $G) (Mat-Mul $A $G)
        # V = V G
        $V = Mat-Mul $V $G
    }
    $evals = @($A[0][0], $A[1][1], $A[2][2])
    return @($evals, $V)
}

# ============================================================
# Umeyama 对齐 (带 scale)
# 输入: $srcPts, $dstPts 为 @(x,y,z) 数组
# 返回: @(R, s, t) — 旋转矩阵, 尺度, 平移
# ============================================================
function Umeyama-Align {
    param($srcPts, $dstPts)
    $n = $srcPts.Count

    # 1. 质心
    $cx = @(0,0,0); $cy = @(0,0,0)
    for ($i=0; $i -lt $n; $i++) {
        for ($d=0; $d -lt 3; $d++) { $cx[$d] += $srcPts[$i][$d]; $cy[$d] += $dstPts[$i][$d] }
    }
    for ($d=0; $d -lt 3; $d++) { $cx[$d] /= $n; $cy[$d] /= $n }

    # 2. 中心化
    $Xc = @(); $Yc = @()
    for ($i=0; $i -lt $n; $i++) {
        $Xc += ,@(($srcPts[$i][0]-$cx[0]),($srcPts[$i][1]-$cx[1]),($srcPts[$i][2]-$cx[2]))
        $Yc += ,@(($dstPts[$i][0]-$cy[0]),($dstPts[$i][1]-$cy[1]),($dstPts[$i][2]-$cy[2]))
    }

    # 3. 交叉协方差 H = Xc^T Yc
    $H = @(@(0,0,0),@(0,0,0),@(0,0,0))
    for ($i=0; $i -lt 3; $i++) {
        for ($j=0; $j -lt 3; $j++) {
            $s = 0.0
            for ($k=0; $k -lt $n; $k++) { $s += $Xc[$k][$i] * $Yc[$k][$j] }
            $H[$i][$j] = $s / $n
        }
    }

    # 4. SVD: 对 H^T H 做特征分解得到 V 和 S
    $Ht = Mat-Trans $H
    $HtH = Mat-Mul $Ht $H
    $eigResult = Eigen-Decomp $HtH
    $evals = $eigResult[0]
    $V = $eigResult[1]

    # 排序特征值 (降序), 同步排列 V 的列
    $idx = @(0,1,2)
    for ($i=0; $i -lt 2; $i++) {
        for ($j=$i+1; $j -lt 3; $j++) {
            if ($evals[$idx[$j]] -gt $evals[$idx[$i]]) {
                $tmp = $idx[$i]; $idx[$i] = $idx[$j]; $idx[$j] = $tmp
            }
        }
    }
    $Vsorted = @(@(0,0,0),@(0,0,0),@(0,0,0))
    for ($j=0; $j -lt 3; $j++) {
        for ($i=0; $i -lt 3; $i++) { $Vsorted[$i][$j] = $V[$i][$idx[$j]] }
    }
    $V = $Vsorted
    $sortedEvals = @($evals[$idx[0]], $evals[$idx[1]], $evals[$idx[2]])
    $singularValues = @([Math]::Sqrt([Math]::Max($sortedEvals[0],0)),
                        [Math]::Sqrt([Math]::Max($sortedEvals[1],0)),
                        [Math]::Sqrt([Math]::Max($sortedEvals[2],0)))

    # 5. U = H V S^(-1)
    $Sinv = @(@(0,0,0),@(0,0,0),@(0,0,0))
    for ($i=0; $i -lt 3; $i++) {
        if ($singularValues[$i] -gt 1e-12) { $Sinv[$i][$i] = 1.0 / $singularValues[$i] }
    }
    $U = Mat-Mul (Mat-Mul $H $V) $Sinv

    # 6. 修正反射: d = sign(det(V U^T))
    $VUt = Mat-Mul $V (Mat-Trans $U)
    $d = [Math]::Sign((Mat-Det $VUt))

    # 7. R = V diag(1,1,d) U^T
    $D = Eye3; $D[2][2] = $d
    $R = Mat-Mul (Mat-Mul $V $D) (Mat-Trans $U)

    # 8. 尺度 s = trace(S * D) / var(X)
    $varX = 0.0
    for ($i=0; $i -lt $n; $i++) {
        for ($d=0; $d -lt 3; $d++) { $varX += $Xc[$i][$d] * $Xc[$i][$d] }
    }
    $varX /= $n
    $traceSD = 0.0
    for ($i=0; $i -lt 3; $i++) { $traceSD += $singularValues[$i] * $D[$i][$i] }
    $s = 1.0
    if ($varX -gt 1e-12) { $s = $traceSD / $varX }

    # 9. t = cy - s * R * cx
    $Rcx = Mat-VecMul $R $cx
    $t = @(($cy[0]-$s*$Rcx[0]), ($cy[1]-$s*$Rcx[1]), ($cy[2]-$s*$Rcx[2]))

    return @($R, $s, $t)
}

# ============================================================
# 主流程
# ============================================================
Write-Host "Reading trajectories..."
$gt = Read-Traj $GtFile
$est = Read-Traj $EstFile

$gtKeys = @($gt.Keys)
$estKeys = @($est.Keys)
Write-Host "GT poses: $($gtKeys.Count), Est poses: $($estKeys.Count)"

# 匹配最近时间戳 (max diff 0.02s)
$matchedSrc = @()
$matchedDst = @()
foreach ($et in $estKeys) {
    $bestDiff = [double]::MaxValue
    $bestKey = $null
    foreach ($gk in $gtKeys) {
        $d = [Math]::Abs($gk - $et)
        if ($d -lt $bestDiff) { $bestDiff = $d; $bestKey = $gk }
    }
    if ($bestDiff -lt 0.02 -and $null -ne $bestKey) {
        $matchedSrc += ,@($est[$et][0], $est[$et][1], $est[$et][2])
        $matchedDst += ,@($gt[$bestKey][0], $gt[$bestKey][1], $gt[$bestKey][2])
    }
}

Write-Host "Matched pairs: $($matchedSrc.Count)"

if ($matchedSrc.Count -lt 3) {
    Write-Host "ERROR: Too few matched pairs!"
    exit 1
}

# Umeyama 对齐
Write-Host "Computing Umeyama alignment..."
$align = Umeyama-Align $matchedSrc $matchedDst
$R = $align[0]
$s = $align[1]
$t = $align[2]
Write-Host "Scale: $([Math]::Round($s, 6))"
Write-Host "Translation: $([Math]::Round($t[0],4)), $([Math]::Round($t[1],4)), $([Math]::Round($t[2],4))"

# 计算对齐后 ATE
$errors = @()
for ($i = 0; $i -lt $matchedSrc.Count; $i++) {
    $Rsrc = Mat-VecMul $R $matchedSrc[$i]
    $aligned = @(($s*$Rsrc[0]+$t[0]), ($s*$Rsrc[1]+$t[1]), ($s*$Rsrc[2]+$t[2]))
    $err = [Math]::Sqrt(
        [Math]::Pow($aligned[0]-$matchedDst[$i][0], 2) +
        [Math]::Pow($aligned[1]-$matchedDst[$i][1], 2) +
        [Math]::Pow($aligned[2]-$matchedDst[$i][2], 2)
    )
    $errors += $err
}

$sumSq = 0.0
foreach ($e in $errors) { $sumSq += $e * $e }
$rmse = [Math]::Sqrt($sumSq / $errors.Count)
$sorted = $errors | Sort-Object
$mean = ($errors | Measure-Object -Average).Average
$median = $sorted[[int]($sorted.Count / 2)]

Write-Host ""
Write-Host "=== ATE Results (Umeyama aligned) ==="
Write-Host "  Matched poses: $($errors.Count)"
Write-Host "  Scale factor: $([Math]::Round($s, 6))"
Write-Host "  RMSE:   $([Math]::Round($rmse, 6)) m"
Write-Host "  Mean:   $([Math]::Round($mean, 6)) m"
Write-Host "  Median: $([Math]::Round($median, 6)) m"
Write-Host "  Min:    $([Math]::Round($sorted[0], 6)) m"
Write-Host "  Max:    $([Math]::Round($sorted[-1], 6)) m"

# 与之前结果对比
Write-Host ""
Write-Host "=== Comparison ==="
$baseline = 0.37
$m3 = 0.2197
$improvement = (($m3 - $rmse) / $m3) * 100
Write-Host "  Baseline (no filter):  $baseline m"
Write-Host "  M3 (semantic only):    $m3 m"
Write-Host "  M4 (semantic+epipolar): $([Math]::Round($rmse, 4)) m"
if ($rmse -lt $m3) {
    Write-Host "  M4 improvement over M3: $([Math]::Round($improvement, 1))%"
} else {
    Write-Host "  M4 vs M3: $([Math]::Round(-$improvement, 1))% change"
}
