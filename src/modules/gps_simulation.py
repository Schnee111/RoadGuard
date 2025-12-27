# Contoh logika sederhana
def get_simulated_gps(frame_count, start_lat=-6.9175, start_lon=107.6191):
    # Asumsi: Setiap frame bergerak 0.00001 derajat ke Timur
    offset = frame_count * 0.00001
    return start_lat, start_lon + offset