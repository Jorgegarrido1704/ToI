<?php 

require_once 'app.php';
$date = date('Y-m-d');

$qry = "SELECT estado, fecha FROM lecturas 
        WHERE fecha BETWEEN '$date 07:30:00' AND '$date 15:30:00' 
        AND maquina = 'M1' 
        ORDER BY fecha ASC, id ASC";

$colection = $conn->query($qry);

$paros =$parosSinMicrosegundos = 0;
$running =$runningSinMicrosegundos = 0;

$lastTiempo = null;
$lasStatus = null;

foreach ($colection as $row) {
    $estatus = $row['estado'];  
    $fechaActual = strtotime($row['fecha']);

    if ($lastTiempo === null) {
        $lastTiempo = $fechaActual;
        $lasStatus = $estatus;
        continue;
    }

    
    $diffTimeSeconds = abs($fechaActual - $lastTiempo);
    $diffTimeMinutes = round($diffTimeSeconds / 60, 2);
   
    
    if ($lasStatus == "STOP" && $diffTimeSeconds > 3) {
        $parosSinMicrosegundos += $diffTimeMinutes;
    } else {
        $runningSinMicrosegundos += $diffTimeMinutes;
    }
    if ($lasStatus == "STOP") {
        $paros += $diffTimeMinutes;
    } else {
        $running += $diffTimeMinutes;
    }

    $lastTiempo = $fechaActual;
    $lasStatus = $estatus;
}

$paros = round($paros, 2);
$running = round($running, 2);
$TiempoInicial = strtotime('07:30:00'); 
$tiempoAhora = strtotime(date('H:i:s'));
$diferenciaDeTiempo= ABS($tiempoAhora - $TiempoInicial);
$diferenciaDeTiempo = round($diferenciaDeTiempo / 60, 2);
if($diferenciaDeTiempo > 30){
    $diferenciaDeTiempo = $diferenciaDeTiempo - 30;
}

$oee= round(($running / $diferenciaDeTiempo) * 100, 2);

$datos = array(
    "paros" => $paros,
    "running" => $running,
    "OEE"=> $oee,
    "parosSinMicrosegundos" => $parosSinMicrosegundos,
    "runningSinMicrosegundos" => $runningSinMicrosegundos,
    "OEEWo" => round(($runningSinMicrosegundos / $diferenciaDeTiempo) * 100, 2)

);

echo json_encode($datos);
$conn->close();