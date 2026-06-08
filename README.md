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

Variables can be any of the following types:

* boolean
* int
* float
* list
* function
* typ
* string literal

They are always public. Most types are mutable, but **typ objects are immutable** - use `kopia av` to create modified copies.

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
| resten av <left> delat med <right> | equivalent to % in other languages |

(this table also applies for float values)

### set modulo variable
```
sätt x till 10
sätt y till resten av x delat med 3
skriv y
```

outputs: `1`

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

`typ` works like structs in other languages. Define fields on separate indented lines
after the `typ` declaration, each with a type annotation using `som`.

```
typ person
    namn som sträng
    ålder som heltal

sätt p till person med David, 37

skriv namn från p
skriv ny rad
skriv ålder från p
```

outputs:
```
David
37
```

Fields are defined one per line inside the `typ` block. Each field name is
followed by `som` and its type. Supported types include `heltal`, `sträng`,
`flyttal`, `boolesk`, `lista`, `grej`, and any user-defined `typ`.

**Generic types** use `av` to specify type parameters:

```
typ par av nyckeltyp, värdetyp
    nyckel som nyckeltyp
    värde som värdetyp

typ ordlista av nyckeltyp, värdetyp
    värden som lista av par av nyckeltyp, värdetyp
```

Type parameters declared after `av` can be used as types for the fields.

### Inheritance

Use `ärver` to inherit fields from a parent type. Parent fields come first
in the constructor:

```
typ fordon
    hastighet som heltal

typ bil ärver fordon
    märke som sträng

sätt min bil till bil med 120, Volvo
skriv hastighet från min bil
skriv ny rad
skriv märke från min bil
```

outputs:
```
120
Volvo
```

`bil` inherits `hastighet` from `fordon`, so `bil med 120, Volvo` sets
`hastighet` first, then `märke`. Inheritance also works with generics:

```
typ ordlista av K, V ärver lista av par av K, V
    extra_fält som heltal
```

To access the variables in a `typ`, use the `från` keyword followed by the variable name.

**Types are immutable** - use `kopia av` to create a modified copy:

```
sätt p till person med David, 37
sätt äldre person till kopia av p med ålder 38
skriv ålder från p
skriv ny rad
skriv ålder från äldre person
```

outputs:
```
37
38
```

The original `p` remains unchanged - `kopia av` creates a new instance with the specified properties updated.

You can update multiple properties at once:

```
sätt p till person med David, 37
sätt uppdaterad person till kopia av p med namn Eva, ålder 38
```

### Named arguments

All three constructs (`typ`, `grej`, and `kopia av`) support **named arguments** in addition to positional arguments.

**Named arguments for `typ` constructors:**

```
typ person
    namn som sträng
    ålder som heltal

. Using named arguments (any order)
sätt p till person med ålder 37, namn David

. Named arguments in field order also works
sätt q till person med namn Eva, ålder 25

. Positional arguments still work
sätt r till person med David, 37
```

**Named arguments for `grej` functions:**

```
sätt add till grej med a, b
    ge a plus b

. Using named arguments (any order)
sätt resultat till add med b 3, a 5
skriv resultat

. Named arguments in param order also works
sätt resultat till add med a 5, b 3
skriv resultat

. Positional arguments still work
sätt resultat till add med 10, 3
skriv resultat
```

outputs:
```
8
8
7
```

**Named arguments for `kopia av`:**

```
sätt p till person med David, 37
sätt uppdaterad till kopia av p med ålder 40, namn Eva
skriv namn från uppdaterad
skriv ny rad
skriv ålder från uppdaterad
```

outputs:
```
Eva
40
```

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

## öka, minska, gångra and dela

To modify a variable in-place (equivalent to `+=`, `-=`, `*=`, `/=`), use these keywords followed by the variable name, the keyword `med`, and the amount:

### öka and minska

```
sätt poäng till 10
öka poäng med 5
skriv poäng
skriv ny rad

minska poäng med 3
skriv poäng
```

outputs:
```
15
12
```

Incrementing (`öka`) also supports string concatenation when used on string variables:

```
sätt ord till hej
öka ord med då
skriv ord
```

outputs:
```
hejdå
```

### gångra and dela (or multiplicera and dividera)

Multiplication and division assignments support both standard and informal Swedish verbs for ease of use:

```
sätt poäng till 10
gångra poäng med 3    . can also use: multiplicera poäng med 3
skriv poäng
skriv ny rad

dela poäng med 2      . can also use: dividera poäng med 2
skriv poäng
```

outputs:
```
30
15.0
```

Multiplying a string by an integer replicates the string:

```
sätt ord till ja
gångra ord med 3
skriv ord
```

outputs:
```
jajaja
```

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
försök
    sätt rader till lista
    
    medan inte i slutet från data
        sätt nuvarande rad till nästa rad från data
        lägg till nuvarande rad i rader
        
    skriv längd från rader
slutligen
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
försök
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
använd bibliotek.exempel
använd mattematik som matte

sätt s till slumpa från matte
skriv s
skriv ny rad
skriv min variabel
```

### Import modes

**Without `som`**: `använd bibliotek.exempel`
All variables from the module are imported directly into the current scope. Use this when you want to access variables directly without a namespace prefix.

**With `som`**: `använd mattematik som matte`
Creates a namespace alias. Access variables through the alias: `slumpa från matte`.

**Conflict handling**: If two modules export the same variable name and both are imported without `som`, the compiler will raise an error. Use `som` to create aliases in that case.

