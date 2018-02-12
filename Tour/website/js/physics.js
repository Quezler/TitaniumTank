var potatoes = [
	document.getElementById("potato1"),
	document.getElementById("potato2"),
	document.getElementById("potato3"),
	document.getElementById("potato4"),
	document.getElementById("potato5"),
	document.getElementById("potato6"),
	document.getElementById("potato7"),
	document.getElementById("potato8"),
	document.getElementById("potato9")
];

var vecX = 6.5;

var potatoesVec = [
	{x: -vecX, y: 2},
	{x: vecX, y: 2},
	{x: -vecX, y: 2},
	{x: vecX, y: 2},
	{x: -vecX, y: 2},
	{x: vecX, y: 2},
	{x: -vecX, y: 2},
	{x: vecX, y: 2},
	{x: -vecX, y: 2}
];

var g = 0.5, absorption = 0.98;

var potatoesPos = [
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)},
	{x: Math.floor(Math.random() * window.innerWidth), y: Math.floor(Math.random() * 400), a:Math.floor(Math.random() * 360)}
];

// main calculation of the animation using a particle and a vector
function move_potatoes()
{
	for(var i = 0; i < 9; i++)
	{
		potatoesPos[i].x += potatoesVec[i].x;               // update position with vector
		potatoesPos[i].y += potatoesVec[i].y;
		
		if (potatoesVec[i].x > 0)
			potatoesPos[i].a += (10+Math.floor(Math.random() * 2));
		else
			potatoesPos[i].a -= (10+Math.floor(Math.random() * 2));
		potatoesPos[i].a = potatoesPos[i].a % 360;
		potatoesVec[i].y += g;                   // update vector with gravity
		if (potatoesPos[i].y > window.innerHeight-100)
		{       // hit da floor, bounce
			potatoesPos[i].y = window.innerHeight-100;           // force position = max bottom
			potatoesVec[i].y = -potatoesVec[i].y * absorption;  // reduce power with absorption
		}
	
		if (potatoesPos[i].x < 0 || potatoesPos[i].x > window.innerWidth)
			potatoesVec[i].x = -potatoesVec[i].x + 0.1;
	}
}

// animate
(function loop()
{
	move_potatoes();
	for(var i = 0; i < 9; i++)
		update_potatoes(potatoes[i], potatoesPos[i]);
	requestAnimationFrame(loop)
})();

function update_potatoes(el, p)
{
	el.style.transform = el.style.webkitTransform = "translate("+p.x+"px,"+p.y+"px) rotate("+p.a+"deg)";
}