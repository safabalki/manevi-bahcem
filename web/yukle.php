<?php
// Manevi Bahçem istatistik sitesi: veri.json'u yalnızca GitHub Actions (safabalki/manevi-bahcem, main dalı) günceller.
// Kimlik: Actions'ın OIDC belgesi (RS256 JWT) GitHub'ın açık anahtarlarıyla doğrulanır; paylaşılan şifre yok.
// PHP 5.6 uyumlu yazıldı (sunucu hesap geneli 5.6).

define('DEPO', 'safabalki/manevi-bahcem');
define('DAL', 'refs/heads/main');
define('KITLE', 'manevibahcem-site');
define('YAYINCI', 'https://token.actions.githubusercontent.com');
define('JWKS_ONBELLEK', __DIR__ . '/.jwks.json');

header('Content-Type: application/json; charset=utf-8');

function bitir($kod, $mesaj) {
    http_response_code($kod);
    echo json_encode(array('ok' => $kod == 200, 'mesaj' => $mesaj));
    exit;
}

function b64url($s) {
    $s = strtr($s, '-_', '+/');
    $ek = strlen($s) % 4;
    if ($ek) { $s .= str_repeat('=', 4 - $ek); }
    return base64_decode($s);
}

function der_uzunluk($n) {
    if ($n < 128) { return chr($n); }
    $b = '';
    while ($n > 0) { $b = chr($n & 0xff) . $b; $n >>= 8; }
    return chr(0x80 | strlen($b)) . $b;
}

function der_tamsayi($b) {
    if (ord($b[0]) > 0x7f) { $b = "\0" . $b; }
    return "\x02" . der_uzunluk(strlen($b)) . $b;
}

// JWK (n, e) → PEM açık anahtar (SubjectPublicKeyInfo)
function jwk_pem($n, $e) {
    $rsa = der_tamsayi(b64url($n)) . der_tamsayi(b64url($e));
    $rsa = "\x30" . der_uzunluk(strlen($rsa)) . $rsa;
    $algo = "\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00";
    $bit = "\x03" . der_uzunluk(strlen($rsa) + 1) . "\0" . $rsa;
    $spki = "\x30" . der_uzunluk(strlen($algo . $bit)) . $algo . $bit;
    return "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($spki), 64, "\n") . "-----END PUBLIC KEY-----\n";
}

function jwks_getir($yenile) {
    if (!$yenile && is_file(JWKS_ONBELLEK) && filemtime(JWKS_ONBELLEK) > time() - 86400) {
        return json_decode(file_get_contents(JWKS_ONBELLEK), true);
    }
    $ch = curl_init(YAYINCI . '/.well-known/jwks');
    curl_setopt_array($ch, array(CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15));
    $govde = curl_exec($ch);
    curl_close($ch);
    $jwks = json_decode($govde, true);
    if (!isset($jwks['keys'])) { bitir(502, 'GitHub anahtarları alınamadı'); }
    file_put_contents(JWKS_ONBELLEK, $govde);
    return $jwks;
}

function dogrula($jwt) {
    $parca = explode('.', $jwt);
    if (count($parca) != 3) { bitir(401, 'Belge biçimi hatalı'); }
    $baslik = json_decode(b64url($parca[0]), true);
    $icerik = json_decode(b64url($parca[1]), true);
    if (!$baslik || !$icerik || !isset($baslik['kid']) || $baslik['alg'] !== 'RS256') { bitir(401, 'Belge başlığı hatalı'); }
    $anahtar = null;
    foreach (array(false, true) as $yenile) {
        foreach (jwks_getir($yenile)['keys'] as $k) {
            if ($k['kid'] === $baslik['kid']) { $anahtar = $k; break 2; }
        }
    }
    if (!$anahtar) { bitir(401, 'Anahtar bulunamadı'); }
    $tamam = openssl_verify($parca[0] . '.' . $parca[1], b64url($parca[2]), jwk_pem($anahtar['n'], $anahtar['e']), OPENSSL_ALGO_SHA256);
    if ($tamam !== 1) { bitir(401, 'İmza geçersiz'); }
    $simdi = time();
    if ($icerik['iss'] !== YAYINCI || $icerik['aud'] !== KITLE) { bitir(403, 'Yayıncı/kitle uyuşmuyor'); }
    if ($icerik['repository'] !== DEPO || $icerik['ref'] !== DAL) { bitir(403, 'Depo/dal izinli değil'); }
    if ($icerik['exp'] < $simdi - 60 || (isset($icerik['nbf']) && $icerik['nbf'] > $simdi + 60)) { bitir(401, 'Belge süresi geçmiş'); }
    return $icerik;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { bitir(405, 'Yalnızca POST'); }
$yetki = isset($_SERVER['HTTP_AUTHORIZATION']) ? $_SERVER['HTTP_AUTHORIZATION'] : '';
if ($yetki === '' && function_exists('getallheaders')) {
    foreach (getallheaders() as $ad => $deger) { if (strtolower($ad) === 'authorization') { $yetki = $deger; } }
}
if (stripos($yetki, 'Bearer ') !== 0) { bitir(401, 'Belge yok'); }
dogrula(trim(substr($yetki, 7)));

$govde = file_get_contents('php://input');
$veri = json_decode($govde, true);
if (!is_array($veri) || !isset($veri['guncelleme']) || strlen($govde) > 2000000) { bitir(400, 'Veri hatalı'); }
file_put_contents(__DIR__ . '/veri.json', $govde, LOCK_EX);

// Günlük geçmiş (büyüme grafiği için): her gün için son toplamlar
$gecmis_yol = __DIR__ . '/gecmis.json';
$gecmis = is_file($gecmis_yol) ? json_decode(file_get_contents($gecmis_yol), true) : array();
if (!is_array($gecmis)) { $gecmis = array(); }
$gun = substr($veri['guncelleme'], 0, 10);
$ozet = array('tarih' => $gun);
foreach (array('youtube', 'instagram', 'facebook') as $p) {
    if (isset($veri['platformlar'][$p]['takipci'])) { $ozet[$p] = $veri['platformlar'][$p]['takipci']; }
}
if (isset($veri['platformlar']['youtube']['izlenme'])) { $ozet['youtube_izlenme'] = $veri['platformlar']['youtube']['izlenme']; }
$gecmis = array_values(array_filter($gecmis, function ($g) use ($gun) { return $g['tarih'] !== $gun; }));
$gecmis[] = $ozet;
file_put_contents($gecmis_yol, json_encode($gecmis), LOCK_EX);

bitir(200, 'Güncellendi');
