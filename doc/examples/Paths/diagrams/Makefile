prefix:= 
synopsis:= python synopsis.py

src	:= ../src/Shapes.h
syn	:= Shapes.syn

all: Files.png Classes1.png Classes2.png Classes3.png

Files.png: $(syn)
	$(synopsis) files --output=$@ $(src)

Classes1.png:
	$(synopsis) classes --output=$@ $(src)

Classes2.png: $(syn)
	$(synopsis) dot hide_attributes=False hide_operations=False --output=$@ $<

Classes3.png: $(syn)
	$(synopsis) dot hide_attributes=False hide_operations=False show_aggregation=True --output=$@ $<

Shapes.syn: $(src)
	$(synopsis) cxx --output=$@ $<

install-html: all
ifdef prefix
	mkdir -p $(prefix)
	cp index.html *.png $(prefix)
endif

install-print: all
ifdef prefix
	mkdir -p $(prefix)
	cp *.png $(prefix)
endif

clean:
	rm -f $(syn)

distclean: clean
	rm -f *.png
