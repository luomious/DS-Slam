"""Pure Python Umeyama-aligned ATE evaluation (no numpy dependency)."""
import sys, math

def read_traj(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            if len(p) >= 4:
                ts = float(p[0])
                if ts not in d:
                    d[ts] = [float(p[1]), float(p[2]), float(p[3])]
    return d

def mat_mul(A, B):
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def mat_T(A):
    return [[A[j][i] for j in range(3)] for i in range(3)]

def mat_vec(A, v):
    return [sum(A[i][k]*v[k] for k in range(3)) for i in range(3)]

def mat_det(A):
    return (A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
           -A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
           +A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))

def eye3():
    return [[1,0,0],[0,1,0],[0,0,1]]

def eigen_decomp(M):
    """Jacobi eigenvalue decomposition for 3x3 symmetric matrix."""
    A = [row[:] for row in M]
    V = eye3()
    for _ in range(200):
        mx, p, q = 0.0, 0, 1
        for i in range(3):
            for j in range(i+1, 3):
                if abs(A[i][j]) > mx:
                    mx = abs(A[i][j]); p, q = i, j
        if mx < 1e-12:
            break
        if abs(A[p][p] - A[q][q]) < 1e-15:
            theta = math.pi / 4
        else:
            theta = 0.5 * math.atan2(2*A[p][q], A[p][p]-A[q][q])
        c, s = math.cos(theta), math.sin(theta)
        G = eye3(); G[p][p]=c; G[q][q]=c; G[p][q]=-s; G[q][p]=s
        A = mat_mul(mat_T(G), mat_mul(A, G))
        V = mat_mul(V, G)
    return [A[0][0], A[1][1], A[2][2]], V

def umeyama(src, dst, force_scale=None):
    n = len(src)
    cx = [sum(src[i][d] for i in range(n))/n for d in range(3)]
    cy = [sum(dst[i][d] for i in range(n))/n for d in range(3)]

    Xc = [[src[i][d]-cx[d] for d in range(3)] for i in range(n)]
    Yc = [[dst[i][d]-cy[d] for d in range(3)] for i in range(n)]

    H = [[sum(Xc[k][i]*Yc[k][j] for k in range(n))/n for j in range(3)] for i in range(3)]

    HtH = mat_mul(mat_T(H), H)
    evals, V = eigen_decomp(HtH)
    idx = sorted(range(3), key=lambda i: evals[i], reverse=True)
    V = [[V[i][idx[j]] for j in range(3)] for i in range(3)]
    sv = [math.sqrt(max(evals[idx[i]], 0)) for i in range(3)]

    Sinv = [[(1/sv[i] if sv[i]>1e-12 else 0) if i==j else 0 for j in range(3)] for i in range(3)]
    U = mat_mul(mat_mul(H, V), Sinv)

    d = math.copysign(1, mat_det(mat_mul(V, mat_T(U))))
    D = eye3(); D[2][2] = d
    R = mat_mul(mat_mul(V, D), mat_T(U))

    varX = sum(Xc[i][d]**2 for i in range(n) for d in range(3)) / n
    traceSD = sum(sv[i]*D[i][i] for i in range(3))
    s = traceSD / varX if varX > 1e-12 else 1.0

    if force_scale is not None:
        s = force_scale

    Rcx = mat_vec(R, cx)
    t = [cy[d] - s*Rcx[d] for d in range(3)]
    return R, s, t

def main():
    se3_mode = "--se3" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("Usage: eval_ate.py <gt_file> <est_file> [--se3]")
        sys.exit(1)
    gt_file = args[0]
    est_file = args[1]

    gt = read_traj(gt_file)
    est = read_traj(est_file)
    print(f"GT poses: {len(gt)}, Est poses: {len(est)}")

    # Match timestamps (nearest, max diff 0.02s)
    gt_keys = sorted(gt.keys())
    matched_src, matched_dst = [], []
    for et in sorted(est.keys()):
        best_diff, best_k = 1e30, None
        for gk in gt_keys:
            d = abs(gk - et)
            if d < best_diff:
                best_diff = d; best_k = gk
        if best_diff < 0.02 and best_k is not None:
            matched_src.append(est[et])
            matched_dst.append(gt[best_k])

    print(f"Matched pairs: {len(matched_src)}")
    if len(matched_src) < 3:
        print("ERROR: Too few matched pairs!")
        sys.exit(1)

    print("Computing Umeyama alignment...")
    force = 1.0 if se3_mode else None
    R, s, t = umeyama(matched_src, matched_dst, force_scale=force)
    if se3_mode:
        print("  (SE3 mode: scale forced to 1.0)")
    print(f"Scale factor: {s:.6f}")
    print(f"Translation: {t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f}")

    errors = []
    for i in range(len(matched_src)):
        Rsrc = mat_vec(R, matched_src[i])
        aligned = [s*Rsrc[d]+t[d] for d in range(3)]
        err = math.sqrt(sum((aligned[d]-matched_dst[i][d])**2 for d in range(3)))
        errors.append(err)

    rmse = math.sqrt(sum(e**2 for e in errors)/len(errors))
    mean = sum(errors)/len(errors)
    srt = sorted(errors)
    median = srt[len(srt)//2]

    print()
    print("=== ATE Results (Umeyama aligned) ===")
    print(f"  Matched poses: {len(errors)}")
    print(f"  Scale factor: {s:.6f}")
    print(f"  RMSE:   {rmse:.6f} m")
    print(f"  Mean:   {mean:.6f} m")
    print(f"  Median: {median:.6f} m")
    print(f"  Min:    {srt[0]:.6f} m")
    print(f"  Max:    {srt[-1]:.6f} m")

    mode_label = "SE3" if se3_mode else "Sim3"
    print(f"  Alignment: {mode_label}")

if __name__ == "__main__":
    main()
