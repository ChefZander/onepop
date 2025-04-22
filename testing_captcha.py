import hashlib
import time

def generate_sha256_hash(data):
    """Generates the SHA-256 hash of the input data."""
    sha256 = hashlib.sha256()
    sha256.update(data.encode('utf-8'))
    return sha256.hexdigest()

def solve_proof_of_work(captcha_token):
    """
    Solves a simple Proof-of-Work challenge similar to the provided JavaScript.

    Args:
        captcha_token: The token required for the proof-of-work.

    Returns:
        The nonce if the challenge is solved, otherwise None.
    """
    print('Starting Proof-of-Work...')
    if not captcha_token:
        print('Error: Captcha token not found.')
        return None

    difficulty = 14

    print(f'Captcha Token: {captcha_token}')
    print(f'Target Difficulty: {difficulty}')

    nonce = 0
    hash_val = ''
    start_time = time.time()
    max_iterations = 10000000
    iterations = 0
    best_iteration = 0

    while iterations < max_iterations:
        data_to_hash = f"popcap-{captcha_token}-popcap-{nonce}-popcap"
        hash_val = generate_sha256_hash(data_to_hash)

        # Count leading zeros in the hash (hexadecimal representation)
        # Each hex character can represent 4 bits. To check for a certain number of
        # leading zero *bits*, we need to check the hex characters.
        # A '0' hex character means 4 zero bits.
        # A '1' to '7' hex character means fewer than 4 zero bits at the beginning.
        # To simplify for this example based on the JS which likely checks leading '0' characters,
        # we will count the number of leading '0' characters in the hex string.
        total_zero_count = hash_val.count('0')

        if total_zero_count > best_iteration:
            best_iteration = total_zero_count
            elapsed_time = time.time() - start_time
            # Avoid division by zero if duration is 0
            hash_rate = (iterations / elapsed_time) if elapsed_time > 0 else 0
            print(f'Solving... {best_iteration}/{difficulty} {int(hash_rate / 1000)}kH/s')


        if total_zero_count >= difficulty:
            end_time = time.time()
            duration = end_time - start_time
            print(f'Captcha solved! Nonce: {nonce}, Hash: {hash_val}')
            print(f'Time taken: {duration:.2f} seconds')
            print(f'Speed: {iterations / duration:.2f} H/s')
            return nonce

        nonce += 1
        iterations += 1
        # In a real-world scenario, you might add a small delay here
        # to avoid pegging the CPU, similar to setTimeout(..., 0)
        # time.sleep(0) # Uncomment for a slight pause if needed

    print('Max iterations reached. Captcha could not be solved within limits.')
    return None

# --- Testing Implementation ---
if __name__ == "__main__":
    # Replace with a sample captcha token for testing
    test_captcha_token = "8430d8ba-6756-46be-942e-f6b826264338"

    solved_nonce = solve_proof_of_work(test_captcha_token)

    if solved_nonce is not None:
        print(f"Proof-of-Work solved with nonce: {solved_nonce}")
        # In a real application, you would now submit the nonce
        # along with the captcha_token to the server for verification.
    else:
        print("Proof-of-Work failed.")