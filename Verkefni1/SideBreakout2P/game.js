const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

const leftLivesEl = document.getElementById("leftLives");
const rightLivesEl = document.getElementById("rightLives");
const leftScoreEl = document.getElementById("leftScore");
const rightScoreEl = document.getElementById("rightScore");
const brickCountEl = document.getElementById("brickCount");
const modeLabelEl = document.getElementById("modeLabel");

const startOverlay = document.getElementById("startOverlay");
const gameOverOverlay = document.getElementById("gameOverOverlay");
const gameOverTitle = document.getElementById("gameOverTitle");
const gameOverText = document.getElementById("gameOverText");
const startBtn = document.getElementById("startBtn");
const restartBtn = document.getElementById("restartBtn");

const keys = {
    KeyW: false,
    KeyS: false,
    ArrowUp: false,
    ArrowDown: false
};

const PADDLE_HEIGHT = 112;
const PADDLE_WIDTH = 14;
const PADDLE_SPEED = 7;
const BALL_RADIUS = 9;
const BASE_BALL_SPEED = 4.1;
const MAX_BALL_SPEED = 9.6;

const leftPaddle = {
    x: 34,
    y: canvas.height / 2 - PADDLE_HEIGHT / 2,
    w: PADDLE_WIDTH,
    h: PADDLE_HEIGHT
};

const rightPaddle = {
    x: canvas.width - 34 - PADDLE_WIDTH,
    y: canvas.height / 2 - PADDLE_HEIGHT / 2,
    w: PADDLE_WIDTH,
    h: PADDLE_HEIGHT
};

let leftLives = 5;
let rightLives = 5;
let leftScore = 0;
let rightScore = 0;
let gameRunning = false;
let selectedBallMode = 1;
let balls = [];
let bricks = [];

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function updateHud() {
    leftLivesEl.textContent = leftLives;
    rightLivesEl.textContent = rightLives;
    leftScoreEl.textContent = leftScore;
    rightScoreEl.textContent = rightScore;
    brickCountEl.textContent = bricks.length;
    modeLabelEl.textContent = selectedBallMode === 2 ? "2 Balls" : "1 Ball";
}

function createBricks() {
    bricks = [];
    const rows = 6;
    const cols = 5;
    const brickW = 34;
    const brickH = 56;
    const gap = 8;
    const totalW = cols * brickW + (cols - 1) * gap;
    const totalH = rows * brickH + (rows - 1) * gap;
    const startX = canvas.width / 2 - totalW / 2;
    const startY = canvas.height / 2 - totalH / 2;

    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            bricks.push({
                x: startX + col * (brickW + gap),
                y: startY + row * (brickH + gap),
                w: brickW,
                h: brickH,
                hp: 1 + ((row + col) % 2)
            });
        }
    }
}

function createBallFromSide(side) {
    const baseY = canvas.height * (0.25 + Math.random() * 0.5);
    const y = clamp(baseY, BALL_RADIUS + 3, canvas.height - BALL_RADIUS - 3);
    const speed = BASE_BALL_SPEED + Math.random() * 1.4;
    const vy = (Math.random() * 2 - 1) * 2.8;
    const fromLeft = side === "left";

    return {
        x: fromLeft ? canvas.width * 0.22 : canvas.width * 0.78,
        y,
        vx: fromLeft ? speed : -speed,
        vy,
        color: fromLeft ? "#ffd9f2" : "#efe7ff"
    };
}

function setupBalls() {
    if (selectedBallMode === 2) {
        balls = [createBallFromSide("left"), createBallFromSide("right")];
    } else {
        balls = [Math.random() > 0.5 ? createBallFromSide("left") : createBallFromSide("right")];
    }
}

function reflectFromPaddle(ball, paddle, isLeftPaddle) {
    const relative = (ball.y - (paddle.y + paddle.h / 2)) / (paddle.h / 2);
    const normalized = clamp(relative, -1, 1);
    const speed = Math.min(MAX_BALL_SPEED, Math.hypot(ball.vx, ball.vy) + 0.22);
    const angle = normalized * (Math.PI / 3);

    ball.vx = (isLeftPaddle ? 1 : -1) * speed * Math.cos(angle);
    ball.vy = speed * Math.sin(angle);
    ball.x = isLeftPaddle ? paddle.x + paddle.w + BALL_RADIUS : paddle.x - BALL_RADIUS;
}

function handleBrickCollision(ball) {
    for (let i = bricks.length - 1; i >= 0; i--) {
        const b = bricks[i];
        const nearestX = clamp(ball.x, b.x, b.x + b.w);
        const nearestY = clamp(ball.y, b.y, b.y + b.h);
        const dx = ball.x - nearestX;
        const dy = ball.y - nearestY;

        if (dx * dx + dy * dy > BALL_RADIUS * BALL_RADIUS) {
            continue;
        }

        const overlapX = Math.min(Math.abs(ball.x - b.x), Math.abs(ball.x - (b.x + b.w)));
        const overlapY = Math.min(Math.abs(ball.y - b.y), Math.abs(ball.y - (b.y + b.h)));
        if (overlapX < overlapY) {
            ball.vx *= -1;
        } else {
            ball.vy *= -1;
        }

        b.hp -= 1;
        if (b.hp <= 0) {
            bricks.splice(i, 1);
            if (ball.vx < 0) {
                rightScore += 8;
            } else {
                leftScore += 8;
            }
        }
        return;
    }
}

function resetLostBall(index, sideLost) {
    if (!gameRunning) {
        return;
    }
    balls[index] = createBallFromSide(sideLost === "left" ? "right" : "left");
}

function handleBallOut(index, side) {
    if (side === "left") {
        leftLives -= 1;
        rightScore += 12;
    } else {
        rightLives -= 1;
        leftScore += 12;
    }

    if (leftLives <= 0 || rightLives <= 0) {
        endGame();
        return;
    }

    resetLostBall(index, side);
}

function updateBalls() {
    for (let i = 0; i < balls.length; i++) {
        const ball = balls[i];
        ball.x += ball.vx;
        ball.y += ball.vy;

        if (ball.y - BALL_RADIUS <= 0 && ball.vy < 0) {
            ball.y = BALL_RADIUS;
            ball.vy *= -1;
        }
        if (ball.y + BALL_RADIUS >= canvas.height && ball.vy > 0) {
            ball.y = canvas.height - BALL_RADIUS;
            ball.vy *= -1;
        }

        if (
            ball.vx < 0 &&
            ball.x - BALL_RADIUS <= leftPaddle.x + leftPaddle.w &&
            ball.y >= leftPaddle.y &&
            ball.y <= leftPaddle.y + leftPaddle.h
        ) {
            reflectFromPaddle(ball, leftPaddle, true);
        }

        if (
            ball.vx > 0 &&
            ball.x + BALL_RADIUS >= rightPaddle.x &&
            ball.y >= rightPaddle.y &&
            ball.y <= rightPaddle.y + rightPaddle.h
        ) {
            reflectFromPaddle(ball, rightPaddle, false);
        }

        handleBrickCollision(ball);

        if (ball.x + BALL_RADIUS < 0) {
            handleBallOut(i, "left");
            if (!gameRunning) {
                return;
            }
        } else if (ball.x - BALL_RADIUS > canvas.width) {
            handleBallOut(i, "right");
            if (!gameRunning) {
                return;
            }
        }
    }

    if (bricks.length === 0) {
        createBricks();
        leftScore += 20;
        rightScore += 20;
    }
}

function movePaddles() {
    if (keys.KeyW) {
        leftPaddle.y -= PADDLE_SPEED;
    }
    if (keys.KeyS) {
        leftPaddle.y += PADDLE_SPEED;
    }
    if (keys.ArrowUp) {
        rightPaddle.y -= PADDLE_SPEED;
    }
    if (keys.ArrowDown) {
        rightPaddle.y += PADDLE_SPEED;
    }

    leftPaddle.y = clamp(leftPaddle.y, 0, canvas.height - leftPaddle.h);
    rightPaddle.y = clamp(rightPaddle.y, 0, canvas.height - rightPaddle.h);
}

function drawCenterLine() {
    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 10]);
    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.stroke();
    ctx.restore();
}

function drawPaddle(paddle, color) {
    ctx.fillStyle = color;
    ctx.fillRect(paddle.x, paddle.y, paddle.w, paddle.h);
}

function drawBricks() {
    for (const b of bricks) {
        ctx.fillStyle = b.hp === 2 ? "#f06fb0" : "#cc7cff";
        ctx.fillRect(b.x, b.y, b.w, b.h);
        ctx.strokeStyle = "rgba(0, 0, 0, 0.2)";
        ctx.strokeRect(b.x, b.y, b.w, b.h);
    }
}

function drawBalls() {
    for (const ball of balls) {
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, BALL_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = ball.color;
        ctx.fill();
    }
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawCenterLine();
    drawBricks();
    drawPaddle(leftPaddle, "#ff79bc");
    drawPaddle(rightPaddle, "#b28dff");
    drawBalls();
}

function gameLoop() {
    if (gameRunning) {
        movePaddles();
        updateBalls();
        draw();
        updateHud();
    }
    requestAnimationFrame(gameLoop);
}

function endGame() {
    gameRunning = false;
    const winner = leftLives <= 0 ? "Right Player Wins!" : "Left Player Wins!";
    gameOverTitle.textContent = winner;
    gameOverText.textContent = `Final Score - Left: ${leftScore}, Right: ${rightScore}`;
    gameOverOverlay.classList.add("visible");
}

function resetMatch() {
    leftLives = 5;
    rightLives = 5;
    leftScore = 0;
    rightScore = 0;
    leftPaddle.y = canvas.height / 2 - PADDLE_HEIGHT / 2;
    rightPaddle.y = canvas.height / 2 - PADDLE_HEIGHT / 2;
    createBricks();
    setupBalls();
    updateHud();
}

function startGameFromSelection() {
    const checked = document.querySelector('input[name="ballMode"]:checked');
    selectedBallMode = checked ? Number(checked.value) : 1;
    resetMatch();
    startOverlay.classList.remove("visible");
    gameOverOverlay.classList.remove("visible");
    gameRunning = true;
    draw();
}

window.addEventListener("keydown", (event) => {
    if (event.code in keys) {
        keys[event.code] = true;
        event.preventDefault();
    }
});

window.addEventListener("keyup", (event) => {
    if (event.code in keys) {
        keys[event.code] = false;
        event.preventDefault();
    }
});

startBtn.addEventListener("click", startGameFromSelection);
restartBtn.addEventListener("click", startGameFromSelection);

createBricks();
setupBalls();
updateHud();
draw();
gameLoop();
