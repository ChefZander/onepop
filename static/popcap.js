// popcap.js
// PoW Captcha Implementation
// by (c) Zander, 2025
// Released under GPLv3

async function generateSHA256Hash(data) {
    const msgUint8 = new TextEncoder().encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');
    const captchaContainer = document.getElementById('pow-captcha');

    if (captchaContainer) {
        console.log('Captcha container found.');
        setupCaptcha(captchaContainer);
    } else {
        console.error('Element with id="pow-captcha" not found.');
    }
});

function setupCaptcha(container) {
    console.log('Setting up captcha...');

    const infoText = document.createElement('div');
    infoText.textContent = "loading popcap...";
    infoText.id = "popcap-info"

    infoText.style.padding = '10px 15px';
    infoText.style.fontSize = '16px';
    infoText.style.cursor = 'pointer';

    container.appendChild(infoText);

    const solveAndFetch = async () => {
        console.log('Initiating captcha solving process...');
        infoText.textContent = 'popcap: loading captcha...';

        try {
            const response = await fetch("/popcap/wave1");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const captchaToken = await response.text();
            console.log('Fetched captcha token:', captchaToken);
            const captchaTokenField = document.getElementById("captcha_token");
            captchaTokenField.value = captchaToken;
            solveProofOfWork(container, captchaToken);
        } catch (error) {
            console.error('Error fetching captcha token:', error);
            infoText.textContent = 'Error. Try again?';
        }
    };

    solveAndFetch();
}

function solveProofOfWork(container, captchaToken) {
    console.log('Starting Proof-of-Work...');
    const difficulty = 15;

    console.log(`Captcha Token: ${captchaToken}`);
    console.log(`Target Difficulty: ${difficulty}`);

    let nonce = 0;
    let hash = '';
    const startTime = Date.now();
    const maxIterations = 10000000;
    let iterations = 0;
    let bestIteration = 0;
    const infoText = document.getElementById('popcap-info');

    async function performHashStep() {
        if (iterations >= maxIterations) {
            console.error('Max iterations reached. Captcha could not be solved within limits.');
            return;
        }
        const dataToHash = "popcap-" + captchaToken + "-popcap-" + nonce + "-popcap";

        // hash = MD5(dataToHash);
        hash = await generateSHA256Hash(dataToHash);

        const totalZeroCount = (hash.match(/0/g) || []).length;
        if(totalZeroCount > bestIteration) {
            bestIteration = totalZeroCount;

            // purely aesthetic, can leave out if you need performance for one more difficulty
            const rollingDuration = (Date.now() - startTime) / 1000;
            const speedKHS = ((iterations / (rollingDuration > 0 ? rollingDuration : 0.001)) / 1000).toFixed();
            infoText.textContent = `popcap: loading captcha... ${bestIteration}/${difficulty} ${speedKHS} kH/s`;
        }

        if (totalZeroCount >= difficulty) {
            const endTime = Date.now();
            const duration = (endTime - startTime) / 1000;
            console.log(`Captcha solved! Nonce: ${nonce}, Hash: ${hash}`);
            console.log(`Time taken: ${duration.toFixed(2)} seconds`);
            console.log(`Speed: ${(iterations / duration).toFixed(2)} H/s`);

            const infoText = document.getElementById('popcap-info');
            infoText.textContent = 'Captcha Solved!';
            infoText.style.display = "none";

            const imageUrl = `/popcap/wave2?challenge_token=${encodeURIComponent(captchaToken)}&nonce=${encodeURIComponent(nonce)}`;
            const imgElement = document.createElement('img');
            imgElement.src = imageUrl;
            imgElement.classList.add("justify-center");
            imgElement.classList.add("rounded-xl");
            imgElement.style.width = "25%";
            imgElement.style.height = "auto";

            container.appendChild(imgElement);


        } else {
            nonce++;
            iterations++;
            // NEVER USE requestAnimationFrame IT DOESNT WORK
            setTimeout(performHashStep, 0); 
        }
    }
    performHashStep();
}