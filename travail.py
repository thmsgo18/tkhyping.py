from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from functools import partial


class MyClass:
    def method1(self):
        return "Résultat de la méthode 1"

    def method2(self):
        return "Résultat de la méthode 2"

    def method3(self):
        return "Résultat de la méthode 3"


class MyGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 20

        self.label = Label(text="Sélectionnez une méthode :")
        self.add_widget(self.label)

        self.dropdown = DropDown()
        self.populate_dropdown()

        self.button = Button(text="Exécuter")
        self.button.bind(on_release=self.dropdown.open)
        self.add_widget(self.button)

        self.result_label = Label(text="")
        self.add_widget(self.result_label)

    def populate_dropdown(self):
        my_class = MyClass()
        methods = dir(my_class)
        for method_name in methods:
            if not method_name.startswith("__") and callable(getattr(my_class, method_name)):
                btn = Button(text=method_name, size_hint_y=None, height=44)
                btn.bind(on_release=partial(self.execute_method, method_name))
                self.dropdown.add_widget(btn)

        self.dropdown.bind(on_select=self.dropdown_select)

    def execute_method(self, method_name, *args):
        my_class = MyClass()
        method = getattr(my_class, method_name)
        result = method()
        self.result_label.text = result

    def dropdown_select(self, instance, text):
        self.button.text = text
        self.dropdown.dismiss()


class MyApp(App):
    def build(self):
        return MyGUI()


if __name__ == '__main__':
    MyApp().run()
