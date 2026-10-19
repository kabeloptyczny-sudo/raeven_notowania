"""Silnik 33 wskaźników technicznych + sygnały + agregacja ważona."""
import pandas as pd
import numpy as np


def tabela(ticker: str, df: pd.DataFrame) -> dict:
    """Oblicza 33 wskaźniki techniczne i zwraca tabelę z sygnałami."""
    if len(df) < 200:
        return {'error': f'Za mało danych: {len(df)} sesji, potrzeba 200'}

    # Normalizacja kolumn
    df = df.copy()
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col not in df.columns:
            return {'error': f'Brak kolumny {col}'}

    df = df.sort_values('data').reset_index(drop=True)
    c = df['Close']
    open_s = df['Open']
    h = df['High']
    l = df['Low']
    v = df['Volume']
    n = len(df)

    # SMA
    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()

    # EMA
    def ema(s, p):
        return s.ewm(span=p, adjust=False).mean()
    ema21 = ema(c, 21)

    # ADX + DI+/DI-
    def atr(s, p=14):
        tr1 = h - l
        tr2 = (h - c.shift()).abs()
        tr3 = (l - c.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(p).mean()

    tr = atr(h, 14)
    up = h - h.shift()
    down = l.shift() - l
    p_up = ((up > 0) * up).rolling(14).mean()
    p_down = ((down > 0) * down).rolling(14).mean()
    di_plus = 100 * p_up / tr
    di_minus = 100 * p_down / tr
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus)
    adx = dx.rolling(14).mean()

    # RSI
    def rsi(s, p=14):
        d = s.diff()
        g = d.clip(lower=0).rolling(p).mean()
        l = (-d).clip(lower=0).rolling(p).mean()
        return 100 - 100 / (1 + g / l)

    rsi14 = rsi(c, 14)

    # MACD
    macd_line = ema(c, 12) - ema(c, 26)
    signal = ema(macd_line, 9)
    hist = macd_line - signal

    # Stochastic
    low14 = l.rolling(14).min()
    high14 = h.rolling(14).max()
    k14 = 100 * (c - low14) / (high14 - low14)
    d3 = k14.rolling(3).mean()

    # Williams %R
    willr = -100 * (high14 - c) / (high14 - low14)

    # CCI
    tp = (h + l + c) / 3
    ma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())))
    cci20 = (tp - ma_tp) / (0.015 * mad)

    # ROC
    roc12 = c.pct_change(12) * 100

    # Momentum
    mom10 = c - c.shift(11)

    # ATR%
    atr_pct = (tr.iloc[-1] / c.iloc[-1]) * 100 if tr.iloc[-1] else 0

    # Bollinger
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_pctb = (c - bb_lower) / (bb_upper - bb_lower)
    bb_bw = (bb_upper - bb_lower) / bb_mid * 100

    # HV
    log_ret = np.log(c / c.shift(1))
    hv20 = log_ret.rolling(20).std() * np.sqrt(252) * 100

    # Keltner
    kc_upper = bb_mid + 2 * tr
    kc_lower = bb_mid - 2 * tr

    # OBV
    obv = (np.sign(c - c.shift()) * v).fillna(0).cumsum()
    obv_sma = obv.rolling(20).mean()

    # CMF
    mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    cmf20 = (mfm * v).rolling(20).sum() / v.rolling(20).sum()

    # MFI
    mfi_tp = (h + l + c) / 3
    mfi_mf = mfi_tp * v
    pos_mf = ((mfi_tp > mfi_tp.shift()) * mfi_mf).rolling(14).sum()
    neg_mf = ((mfi_tp < mfi_tp.shift()) * mfi_mf).rolling(14).sum()
    mfi = 100 - 100 / (1 + pos_mf / neg_mf)

    # 52w
    max52 = c.tail(252).max()
    min52 = c.tail(252).min()

    # Ostatnie wartości
    last_c = c.iloc[-1]
    last_sma20 = sma20.iloc[-1]
    last_sma50 = sma50.iloc[-1]
    last_sma200 = sma200.iloc[-1]
    last_ema21 = ema21.iloc[-1]
    last_rsi = rsi14.iloc[-1]
    last_adx = adx.iloc[-1]
    last_di_plus = di_plus.iloc[-1]
    last_di_minus = di_minus.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal.iloc[-1]
    last_hist = hist.iloc[-1]
    last_k = k14.iloc[-1]
    last_d = d3.iloc[-1]
    last_willr = willr.iloc[-1]
    last_cci = cci20.iloc[-1]
    last_roc = roc12.iloc[-1]
    last_mom = mom10.iloc[-1]
    last_bb_pctb = bb_pctb.iloc[-1]
    last_bb_bw = bb_bw.iloc[-1]
    last_hv = hv20.iloc[-1]
    last_kc_upper = kc_upper.iloc[-1]
    last_kc_lower = kc_lower.iloc[-1]
    last_obv = obv.iloc[-1]
    last_obv_sma = obv_sma.iloc[-1]
    last_cmf = cmf20.iloc[-1]
    last_mfi = mfi.iloc[-1]

    # Wartości formatowane
    def fmt(v, d=2):
        return '—' if pd.isna(v) else f"{v:,.{d}f}".replace(',', ' ')

    wiersze = []

    # --- TREND (waga 0.04) ---
    def add_trend(idx, nazwa, punkty, sygnal, opis, wartosc):
        wiersze.append({
            'grupa': 'TREND', 'nazwa': nazwa, 'wartosc': fmt(wartosc),
            'sygnal': sygnal, 'punkty': punkty, 'waga': 0.04, 'opis': opis
        })

    # 1. SMA 20
    p = 1 if last_c > last_sma20 * 1.01 else (-1 if last_c < last_sma20 * 0.99 else 0)
    s = '+1' if p > 0 else ('-1' if p < 0 else '0')
    add_trend(1, 'SMA 20', p, s, '', last_sma20)

    # 2. SMA 50
    p = 1 if last_c > last_sma50 * 1.02 else (-1 if last_c < last_sma50 * 0.98 else 0)
    s = '+1' if p > 0 else ('-1' if p < 0 else '0')
    add_trend(2, 'SMA 50', p, s, '', last_sma50)

    # 3. SMA 200
    p = 1 if last_c > last_sma200 * 1.03 else (-1 if last_c < last_sma200 * 0.97 else 0)
    s = '+1' if p > 0 else ('-1' if p < 0 else '0')
    add_trend(3, 'SMA 200', p, s, '', last_sma200)

    # 4. EMA 21
    p = 1 if last_c > last_ema21 else -1
    s = '+1' if p > 0 else '-1'
    add_trend(4, 'EMA 21', p, s, '', last_ema21)

    # 5. Układ SMA
    if last_sma20 > last_sma50 > last_sma200:
        p, s, o = 2, '+2', 'S20>S50>S200'
    elif last_sma20 < last_sma50 < last_sma200:
        p, s, o = -2, '-2', 'S20<S50<S200'
    elif last_sma20 > last_sma50:
        p, s, o = 1, '+1', 'S20>S50'
    elif last_sma20 < last_sma50:
        p, s, o = -1, '-1', 'S20<S50'
    else:
        p, s, o = 0, '0', ''
    add_trend(5, 'Układ SMA', p, s, o, last_sma50)

    # 6. Golden/Death cross
    diff50_200 = sma50 - sma200
    diff25 = diff50_200.tail(25)
    if len(diff25) > 1:
        sign_change = (diff25.iloc[-1] > 0) and (diff25.iloc[0] < 0)
        sign_change_neg = (diff25.iloc[-1] < 0) and (diff25.iloc[0] > 0)
        if sign_change:
            p, s, o = 1, '+1', 'Golden cross <25 sesji'
        elif sign_change_neg:
            p, s, o = -1, '-1', 'Death cross <25 sesji'
        else:
            p, s, o = 0, '0', ''
    else:
        p, s, o = 0, '0', ''
    add_trend(6, 'Golden/Death cross', p, s, o, diff50_200.iloc[-1])

    # 7. Nachylenie SMA200
    if len(sma200) >= 21:
        slope = (last_sma200 / sma200.iloc[-21] - 1) * 100
        p = 1 if slope > 2 else (-1 if slope < -2 else 0)
        s = '+1' if p > 0 else ('-1' if p < 0 else '0')
        add_trend(7, 'Nachylenie SMA200 (20d)', p, s, '', slope)
    else:
        add_trend(7, 'Nachylenie SMA200 (20d)', 0, '0', '', 0)

    # 8. ADX + DI
    if pd.notna(last_adx):
        if last_adx > 25:
            p = 2 if last_di_plus > last_di_minus else -2
        elif last_adx > 20:
            p = 1 if last_di_plus > last_di_minus else -1
        else:
            p = 0
        s = f"+{p}" if p > 0 else (f"{p}" if p < 0 else '0')
        o = f"ADX={fmt(last_adx,1)}, DI+={fmt(last_di_plus,1)}, DI-={fmt(last_di_minus,1)}"
    else:
        p, s, o = 0, '0', ''
    add_trend(8, 'ADX(14) + DI+/DI-', p, s, o, last_adx)

    # --- MOMENTUM (waga 0.025) ---
    def add_mom(idx, nazwa, punkty, sygnal, opis, wartosc):
        wiersze.append({
            'grupa': 'MOMENTUM', 'nazwa': nazwa, 'wartosc': fmt(wartosc),
            'sygnal': sygnal, 'punkty': punkty, 'waga': 0.025, 'opis': opis
        })

    # 9. RSI
    if pd.notna(last_rsi):
        if last_rsi < 30 and last_c > last_sma200:
            p, s, o = 2, '+2', 'Oversold + powyżej SMA200'
        elif 30 <= last_rsi < 45 and last_c > last_sma200:
            p, s, o = 1, '+1', '30-45 + powyżej SMA200'
        elif last_rsi > 70 and last_c < last_sma200:
            p, s, o = -1, '-1', 'Overbought + poniżej SMA200'
        elif last_rsi > 80:
            p, s, o = -2, '-2', 'Silny overbought'
        else:
            p, s, o = 0, '0', ''
    else:
        p, s, o = 0, '0', ''
    add_mom(9, 'RSI(14) Wilder', p, s, o, last_rsi)

    # 10. Dywergencja RSI
    rsi30 = rsi14.tail(30)
    if len(rsi30) >= 30:
        p1, p2 = rsi30.iloc[:15], rsi30.iloc[15:]
        c1, c2 = c.tail(30).iloc[:15], c.tail(30).iloc[15:]
        if c2.max() > c1.max() and rsi30.max() < rsi30[:15].max():
            p, s, o = -1, '-1', 'niedźwiedzia'
        elif c2.max() < c1.max() and rsi30.max() > rsi30[:15].max():
            p, s, o = 1, '+1', 'bycza'
        else:
            p, s, o = 0, '0', ''
    else:
        p, s, o = 0, '0', ''
    add_mom(10, 'Dywergencja RSI', p, s, o, 0)

    # 11. MACD vs Signal
    if pd.notna(last_macd) and pd.notna(last_signal):
        if last_macd > last_signal and last_macd > 0:
            p, s = 1, '+1'
        elif last_macd < last_signal and last_macd < 0:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_mom(11, 'MACD vs Signal', p, s, '', last_macd)

    # 12. MACD histogram
    if pd.notna(last_hist):
        hist_trend = hist.tail(5).diff().mean()
        if last_hist > 0 and hist_trend > 0:
            p, s = 2, '+2'
        elif last_hist > 0:
            p, s = 1, '+1'
        elif last_hist < 0 and hist_trend < 0:
            p, s = -2, '-2'
        elif last_hist < 0:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_mom(12, 'MACD histogram', p, s, '', last_hist)

    # 13. Dywergencja MACD
    macd30 = macd_line.tail(30)
    if len(macd30) >= 30:
        c1, c2 = c.tail(30).iloc[:15], c.tail(30).iloc[15:]
        if c2.max() > c1.max() and macd30.max() < macd30[:15].max():
            p, s, o = -1, '-1', 'niedźwiedzia'
        elif c2.max() < c1.max() and macd30.max() > macd30[:15].max():
            p, s, o = 1, '+1', 'bycza'
        else:
            p, s, o = 0, '0', ''
    else:
        p, s, o = 0, '0', ''
    add_mom(13, 'Dywergencja MACD', p, s, o, 0)

    # 14. Stochastic
    if pd.notna(last_k) and pd.notna(last_d):
        if last_k < 20 and last_k > last_d:
            p, s = 2, '+2'
        elif last_k > 80 and last_k < last_d:
            p, s = -2, '-2'
        elif last_k > last_d:
            p, s = 1, '+1'
        elif last_k < last_d:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_mom(14, 'Stochastic(14,3,3)', p, s, '', last_k)

    # 15. Williams %R
    if pd.notna(last_willr):
        p = 1 if last_willr < -80 else (-1 if last_willr > -20 else 0)
        s = '+1' if p > 0 else ('-1' if p < 0 else '0')
    else:
        p, s = 0, '0'
    add_mom(15, 'Williams %R(14)', p, s, '', last_willr)

    # 16. CCI
    if pd.notna(last_cci):
        if last_cci < -100:
            p, s = 1, '+1'
        elif last_cci > 100:
            p, s = -1, '-1'
        elif last_cci > 50:
            p, s = 1, '+1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_mom(16, 'CCI(20)', p, s, '', last_cci)

    # 17. ROC
    if pd.notna(last_roc):
        p = 2 if last_roc > 5 else (1 if last_roc > 0 else (-2 if last_roc < -5 else (-1 if last_roc < 0 else 0)))
        s = f"+{p}" if p > 0 else (f"{p}" if p < 0 else '0')
    else:
        p, s = 0, '0'
    add_mom(17, 'ROC(12)', p, s, '', last_roc)

    # 18. Momentum
    if pd.notna(last_mom):
        p = 1 if last_mom > 0 else -1
        s = '+1' if p > 0 else '-1'
    else:
        p, s = 0, '0'
    add_mom(18, 'Momentum(10)', p, s, '', last_mom)

    # --- ZMIENNOSC (waga 0.02) ---
    def add_vol(idx, nazwa, punkty, sygnal, opis, wartosc):
        wiersze.append({
            'grupa': 'ZMIENNOSC', 'nazwa': nazwa, 'wartosc': fmt(wartosc),
            'sygnal': sygnal, 'punkty': punkty, 'waga': 0.02, 'opis': opis
        })

    # 19. ATR%
    if atr_pct > 5:
        o = 'wysoka'
    elif atr_pct < 1.5:
        o = 'niska'
    else:
        o = 'normalna'
    add_vol(19, 'ATR(14) %', 0, '0', o, atr_pct)

    # 20. Bollinger %B
    if pd.notna(last_bb_pctb):
        if last_bb_pctb < 0.05:
            p, s = 2, '+2'
        elif last_bb_pctb < 0.2:
            p, s = 1, '+1'
        elif last_bb_pctb > 0.95:
            p, s = -2, '-2'
        elif last_bb_pctb > 0.8:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol(20, 'Bollinger %B(20,2)', p, s, '', last_bb_pctb)

    # 21. Bollinger Bandwidth
    if pd.notna(last_bb_bw):
        if last_bb_bw < 4:
            o = 'squeeze'
        elif last_bb_bw > 15:
            o = 'rozstrzelenie'
        else:
            o = 'normalna'
    else:
        o = ''
    add_vol(21, 'Bollinger Bandwidth', 0, '0', o, last_bb_bw)

    # 22. HV 20d
    add_vol(22, 'HV 20d', 0, '0', 'info', last_hv)

    # 23. Keltner position
    if pd.notna(last_kc_upper) and pd.notna(last_kc_lower):
        if last_c < last_kc_lower:
            p, s = 1, '+1'
        elif last_c > last_kc_upper:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol(23, 'Keltner position(20,2*ATR)', p, s, '', last_kc_lower)

    # --- WOLUMEN (waga 0.04) ---
    def add_vol2(idx, nazwa, punkty, sygnal, opis, wartosc):
        wiersze.append({
            'grupa': 'WOLUMEN', 'nazwa': nazwa, 'wartosc': fmt(wartosc),
            'sygnal': sygnal, 'punkty': punkty, 'waga': 0.04, 'opis': opis
        })

    # 24. Volume vs SMA20
    v_sma20 = v.rolling(20).mean()
    last_v = v.iloc[-1]
    last_v_sma = v_sma20.iloc[-1]
    vr = 0
    if pd.notna(last_v_sma) and last_v_sma > 0:
        vr = last_v / last_v_sma
        if vr > 1.5:
            p = 1 if last_c > open_s.iloc[-1] else -1
            s = '+1' if p > 0 else '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol2(24, 'Volume vs SMA20', p, s, '', vr)

    # 25. OBV trend
    if pd.notna(last_obv) and pd.notna(last_obv_sma):
        p = 1 if last_obv > last_obv_sma else -1
        s = '+1' if p > 0 else '-1'
    else:
        p, s = 0, '0'
    add_vol2(25, 'OBV trend', p, s, '', last_obv)

    # 26. CMF
    if pd.notna(last_cmf):
        if last_cmf > 0.25:
            p, s = 2, '+2'
        elif last_cmf > 0.10:
            p, s = 1, '+1'
        elif last_cmf < -0.25:
            p, s = -2, '-2'
        elif last_cmf < -0.10:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol2(26, 'CMF(20)', p, s, '', last_cmf)

    # 27. MFI
    if pd.notna(last_mfi):
        if last_mfi < 20:
            p, s = 2, '+2'
        elif last_mfi < 30:
            p, s = 1, '+1'
        elif last_mfi > 80:
            p, s = -2, '-2'
        elif last_mfi > 70:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol2(27, 'MFI(14)', p, s, '', last_mfi)

    # 28. Volume Spike
    vr = 0
    if pd.notna(v_sma20.iloc[-1]) and v_sma20.iloc[-1] > 0:
        vr = last_v / v_sma20.iloc[-1]
        if vr > 2.0:
            p = 1 if last_c > open_s.iloc[-1] else -1
            s = '+1' if p > 0 else '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_vol2(28, 'Volume Spike', p, s, '', vr)

    # --- STRUKTURA (waga 0.026) ---
    def add_str(idx, nazwa, punkty, sygnal, opis, wartosc):
        wiersze.append({
            'grupa': 'STRUKTURA', 'nazwa': nazwa, 'wartosc': fmt(wartosc),
            'sygnal': sygnal, 'punkty': punkty, 'waga': 0.026, 'opis': opis
        })

    # 29. Pozycja vs 52w max
    if pd.notna(max52):
        if last_c >= 0.98 * max52:
            p, s = 2, '+2'
        elif last_c >= 0.95 * max52:
            p, s = 1, '+1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_str(29, 'Pozycja vs 52w max', p, s, '', max52)

    # 30. Pozycja vs 52w min
    if pd.notna(min52):
        if last_c <= 1.05 * min52:
            p, s = -2, '-2'
        elif last_c <= 1.10 * min52:
            p, s = -1, '-1'
        else:
            p, s = 0, '0'
    else:
        p, s = 0, '0'
    add_str(30, 'Pozycja vs 52w min', p, s, '', min52)

    # 31. Wyższe szczyty/dolki (20d)
    c20 = c.tail(20)
    if len(c20) >= 20:
        p1, p2 = c20.iloc[:10], c20.iloc[10:]
        if p2.max() > p1.max() and p2.min() > p1.min():
            p, s, o = 1, '+1', 'wzrost'
        elif p2.max() < p1.max() and p2.min() < p1.min():
            p, s, o = -1, '-1', 'spadek'
        else:
            p, s, o = 0, '0', ''
    else:
        p, s, o = 0, '0', ''
    add_str(31, 'Wyższe szczyty/dolki (20d)', p, s, o, c20.iloc[-1])

    # 32. Gap
    if n >= 2:
        gap = (df['Open'].iloc[-1] / c.iloc[-2] - 1) * 100
        p = 1 if gap > 1.5 else (-1 if gap < -1.5 else 0)
        s = '+1' if p > 0 else ('-1' if p < 0 else '0')
    else:
        gap, p, s = 0, 0, '0'
    add_str(32, 'Gap', p, s, '', gap)

    # 33. Wzór świec
    last_o = open_s.iloc[-1]
    last_c = c.iloc[-1]
    body = abs(last_c - last_o)
    rng = h.iloc[-1] - l.iloc[-1]
    up_sh = h.iloc[-1] - max(last_c, last_o)
    dn_sh = min(last_c, last_o) - l.iloc[-1]
    if rng > 0:
        body_rng = body / rng
        up_sh_rng = up_sh / rng
        dn_sh_rng = dn_sh / rng
        if body_rng < 0.1:
            p, s, opis = 0, '0', 'doji'
        elif dn_sh_rng > 0.6 and body_rng < 0.3 and last_c > last_o:
            p, s, opis = 2, '+2', 'hammer'
        elif up_sh_rng > 0.6 and body_rng < 0.3 and last_c < last_o:
            p, s, opis = -2, '-2', 'shooting star'
        elif n >= 2 and last_c > last_o and c.iloc[-2] < open_s.iloc[-2] and last_c > open_s.iloc[-2] and last_o < c.iloc[-2]:
            p, s, opis = 2, '+2', 'bullish engulfing'
        elif n >= 2 and last_c < last_o and c.iloc[-2] > open_s.iloc[-2] and last_c < open_s.iloc[-2] and last_o > c.iloc[-2]:
            p, s, opis = -2, '-2', 'bearish engulfing'
        else:
            p, s, opis = 0, '0', ''
    else:
        p, s, opis = 0, '0', ''
    add_str(33, 'Wzór świec', p, s, opis, body)

    # Agregacja
    total = sum(w['punkty'] * w['waga'] for w in wiersze)

    if total >= 1.2:
        reko = 'MOCNO KUPUJ'
    elif total >= 0.4:
        reko = 'KUPUJ'
    elif total <= -1.2:
        reko = 'SPRZEDAJ'
    elif total <= -0.4:
        reko = 'REDUKUJ'
    else:
        reko = 'NEUTRALNIE'

    return {
        'ticker': ticker,
        'cena': float(last_c),
        'data': str(df['data'].iloc[-1].date()),
        'wiersze': wiersze,
        'suma': round(total, 3),
        'rekomendacja': reko
    }
