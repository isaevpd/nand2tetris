// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// declare constants
@24576
D=A
@SCREEN_MAX_VALUE
M=D
@is_filled
M=0


(INPUT_LOOP)
@KBD
D=M
@WHITEN
D;JEQ
// BLACK
@is_filled
D=M
@INPUT_LOOP
D;JGT
@to_fill
M=-1
@is_filled
M=1
@PRE_LOOP
0;JMP
(WHITEN)
@is_filled
D=M
@INPUT_LOOP
D;JEQ
@to_fill
M=0
@is_filled
M=0

(PRE_LOOP)
@SCREEN // fetch initial screen value
D=A // assign it to D
@i // assign it to i
M=D

(LOOP)
@i
D=M // take current value of i
@SCREEN_MAX_VALUE
D=D-M; // subtract screen max value from it
@INPUT_LOOP
D;JEQ // if D[i] - SCREEN_MAX_VALUE is 0 jump to input loop

@to_fill
D=M
@i // otherwise take that register, set it to -1 and increment i
A=M
M=D
@i
M=M+1
@LOOP
0;JMP

