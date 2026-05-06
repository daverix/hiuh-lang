# Hiuh-lang

Hiue is a language that is meant for Swedish people. It uses indentation like python and uses Swedish keywords. Keywords are case insensitive. Everything should be easy to type on a mobile keyword without having to switch to different layouts. A-ö, dots, commas are main symbols used for the language itself.

The goal of this project is to make it compile itself. (bootstrapping)

## stdout

Writing to stdout:

```
skriv hejsan hoppsan
```

will output:
```
hejsan hoppsan
```

New lines uses the keyword `ny rad`:

```
skriv hejsan
skriv ny rad
skriv hoppsan
```

outputs:
```
hejsan
hoppsan
```

## Variables

Variabels can be any of the following types:

* boolean
* int
* float
* list
* function
* typ
* string literal

They are always public and mutable.

Every variable is created and updated using "sätt":

### set boolean variable

Value of a boolean variable can either be SANT, FALSKT or an expression.

```
sätt x till SANT
sätt y till x eller FALSKT

sätt a till 3
sätt b till a större än 2
```

| operator  | description |
|-----------|-------------|
| större än | more than in other languages (>) |
| större än eller lika med | more than or equal to (>=)
| mindre än | less than in other languages (<) |
| mindre än eller lika med | less or equal to (<=) |
| lika med | equals in other languages (==) |
| inte lika med | not equals in other languages (!=) |


### set int variable

```
sätt x till 2
skriv x
```

outputs: `2`

It can also be set to an expression:

```
sätt a till 2
sätt b till a gånger 3
sätt c till b gånger b plus a
```

| operator  | description |
|-----------|-------------|
| plus     | equivalent to + in other languages |
| minus     | equivalent to - in other languages |
| gånger    | equivalent to * in other languages |
| delat med | equivalent to / in other languages |

(this table also applies for float values)

### set float variable
```
sätt y till 3,4
skriv y
```

outputs: `3,4`

### set list variable

empty list:
```
sätt min lista till lista
```

initialize list with values:
```
sätt min lista till lista med 1, 2, 3
```

Note! Here `min lista` is the variable. `lista med` creates a list with the comma separated elements that follows.

### set function variable

```
sätt min funktion till grej med param1, param2, param3
    ge param1 plus param2 minus param3

sätt x till min funktion med 1, 2, 3

skriv x
```

outputs: `0`

Note! The variable `min funktion` is called with parameters 1, 2, 3. `grej` defines the function. Parameters come after `med`.

### set typ variable

`typ` works like structs in other languages.

```
typ person med namn, ålder

sätt p till person med David, 37

skriv Namn
skriv ny rad
skriv namn från p
skriv ny rad
skriv ålder från p
```

outputs:
```
David
37
```

To access the variables in a `typ`, use the `från` keyword followed by the variable name.

To set a variable to a new value in a `typ`, use the following syntax:

```
sätt ålder i person till 38
```

`i` here means that the variable `ålder` is accessed from `person` instead of variables available in the current scope.

### set string literal

Anything specified after "TILL" that does not match any of the other types will be a string:

```
sätt x till en lång fin text som innehåller skriv och kommer inte tolkas som keyword
skriv x
```

outputs:
```
en lång fin text som innehåller skriv och kommer inte tolkas som keyword
```

## if statements

```
sätt x till 3
om x är större än 2
    skriv större
annars
    skriv mindre eller lika med
```

## while loops

```
sätt x till 0
medan x är mindre än 10
    skriv x plus 1
    sätt x till x plus 1
```

outputs: `12345678910`

## stdin

```
sätt nummer som text till nästa rad från inmatning
sätt nummer till konvertera till nummer med nummer som text

om nummer är större än 10
    skriv stort nummer
annars
    skriv litet nummer
```

Outputs `stort nummer` when user types a number larger than 10, `litet nummer` otherwise.

In this example, `nästa rad` reads the next line from stdin into the variable `nummer som text`. It is then converted to a number using the built in function `konvertera till nummer` which takes `nummer som text` as a parameter.


## reading files

```
öppna fil.txt som input
sätt rad1 till nästa rad från input
skriv rad1
stäng input
```

This reads the first row from file `fil.txt`.

`öpnna` and `stäng` are a built in functions for opening and closing files.

`input` is a `typ` variable that contains the variable `nästa rad` (which gives the next row when called)


Reading multiple lines:

```
öppna fil2.txt som data
sätt rader till lista

medan inte i slutet från data
    sätt nuvarande rad till nästa rad från data
    lägg till nuvarande rad i rader
    
skriv längd från rader
stäng data
```

In the example above, `rad finns` is boolean variable in `data` which is assigned from `inläsning` with the file `fil2.txt`.


## saving files

```
sätt text till spara ner detta
sätt output till nedsparning


```


## error handling

If something goes wrong we can catch it by using:

```
prova
    skriv här testar vi något och det blev fel
    skriv ny rad
    kasta något fel här
fånga fel
    skriv det blev ett fel
    skriv ny rad
    skriv meddelande från fel
```

outputs:
```
här testar vi något och det blev fel
det blev ett fel
något fel här
```

## scopes

```
sätt x till 3
sätt y till grej med a
    sätt b till grej med c
        ge c gånger a

    ge b med x delat med a

skriv y med 4

```

In this example `x` is reachable everywhere in the code that follows, calling `sätt x till ...` anywhere after it has been set once will assign it to a new value and accessable by all functions created after it.

`a` is only accessible inside function `y` and function `b`. `c` is only accessible in function `b`.

## comments

If a line starts with `.` in the beginning of the line or after the indent, the text that follows will be a comment and ignored by the compiler:

```
. skriver en text
skriv hej

. jämför något
om längd från hej är större än 2
    . skriver hoppsan för att längden är större än två
    skriv hoppsan
```

## packages

Source code can be put into separate files and be referenced by it's name without the file extension. Slashes are replaced with dots.

In the following tree structure:

```
bibliotek/exempel.hiue
mattematik.hiue
app.hiue
```

`bibliotek/exempel`:

This file exposes the text variable `min variabel` to other files that import it:

```
sätt min variabel till en text
```

`mattematik`:

This file exposes the function variable `slumpa` to other files that import it:

```
sätt slumpa till grej
    ge 42
```

`app.hiue`:

In the example, the main application. When compiling point to the main file and the compiler will pull in all other files relative this file:

```
hämta bibliotek.exempel
hämta mattematik som matte

sätt s till slumpa från matte
skriv nästa tal från s
skriv ny rad
skriv min variabel från exempel
```

